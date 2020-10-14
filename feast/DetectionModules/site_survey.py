"""
The site_survey module defines the site level level survey based detection class, SiteSurvey.
"""
import numpy as np
from .abstract_detection_method import DetectionMethod


class SiteSurvey(DetectionMethod):
    """
    SiteSurvey specifies a site level, survey based detection method. A site level detection method is sensitive to
    the total emissions from a site. If emissions are detected, the site is identified as the source of emissions
    rather than a component on the site. Survey based detection methods search for emissions at a specific moment in
    time (as opposed to monitor detection methods that continuously scan sites for new emissions).
    The class has three essential attributes:

    1. An operating envelope function to determine if the detection method can be applied
    2. A probability of detection surface function to determine which emissions are detected
    3. The ability to dispatch a follow up action
    """
    def __init__(self, time, dispatch_object, sites_per_day, site_cost, detection_probability_points,
                 detection_probabilities, op_envelope={}, ophrs={'begin': 0, 'end': 24}, site_queue=[],
                 survey_interval=None, **kwargs):
        """
        :param time: a Time object
        :param dispatch_object: the object that SiteSurvey will pass flagged site indexes to (DetectionMethod or Repair)
        :param sites_per_day: the number of sites that the method can survey in one day (int)
        :param site_cost: the cost per site of the detection method ($/site--float)
        :param detection_probability_points: The conditions at which the detection probability was measured. (NxM
            array, where N is the number of distinct conditions and M is the number of variables (up to two)).
        :param detection_probabilities: The list of probabilities of detection associated with every point in
            detection_probability_points (array of shape N, where N is the number of conditions with an associated
            probability of detection).
        :param op_envelope: The set of conditions underwhich the SiteSurvey may operate. The op_envelope must be
            passed as a dict with the following form--\n
            {'parameter name': {'class': int, 'min': list of minimum conditions, 'max': list of maximum conditions}}\n
            Unique minima can be defined for every site in a list if the op_envelope 'class' is site specific. Multiple
            minima can be defined in a list for a single site if multiple ranges should be considered.
        :param ophrs: The times of day when the SiteSurvey can be deployed. Should be a dict:\n
            {'begin': hour integer, 'end': hour integer}
        :param site_queue: an ordered list of sites to be surveyed. An LDAR program may update this list.
        :param survey_interval: The time between surveys (int--days)
        """

        DetectionMethod.__init__(self, time, **kwargs)
        self.dispatch_object = dispatch_object

        # --------------- Process Variables -------------------
        self.ophrs = ophrs
        self.op_envelope = op_envelope
        self.survey_interval = survey_interval
        self.sites_per_day = sites_per_day
        self.site_cost = site_cost  # $/site

        # --------------- Detection Variables -----------------
        self.site_queue = site_queue  # queue of sites to survey
        self.detection_probability_points = detection_probability_points
        self.detection_probabilities = detection_probabilities

        # -------------- Set calculated parameters --------------
        work_time = (self.ophrs['end'] - self.ophrs['begin']) / 24
        self.sites_per_timestep = int(self.sites_per_day * (int(time.delta_t) +
                                                            np.min([1, np.mod(time.delta_t, 1) / work_time])))
        if self.sites_per_timestep < 1 and self.sites_per_day > 0:
            print("WARNING: expecting less than 1 site surveyed per timestep. May lead to unexpected behavior.")

    def detect_prob_curve(self, time, gas_field, site_inds, emissions):
        """
        This function determines which sites are passed to the dispatch_object by SiteSurvey.  The function sums all
        emissions at a site, determines the probability of detection given the total site emissions and present
        conditions, then determines whether or not the site is flagged according to the probability.

        :param time: Simulation time object
        :param gas_field: Simulation gas_field object
        :param site_inds: The set of sites to be considered
        :param emissions: an object storing all emissions in the simulation

        :return detect: the indexes of detected leaks
        """

        n_scores = len(site_inds)
        if n_scores == 0:
            return site_inds
        probs = np.zeros(n_scores)
        counter = 0
        for site_ind in site_inds:
            vals = np.zeros(len(self.detection_variables))
            ind = 0
            cond = np.where(emissions.site_index[:emissions.n_em] == site_ind)[0]
            for v, im in self.detection_variables.items():
                if v in gas_field.met:
                    vals[ind] = gas_field.get_met(time, v, interp_modes=im, ophrs=self.ophrs)[v]
                else:
                    # sum all emission variables needed for detection
                    vals[ind] = np.sum(emissions.__getattribute__(v)[cond])
                ind += 1
            prob = self.empirical_interpolator(self.detection_probability_points, self.detection_probabilities, vals)
            probs[counter] = prob
            counter += 1
        scores = np.random.uniform(0, 1, n_scores)
        detect = np.array(site_inds)[scores <= probs]
        return detect

    def sites_surveyed(self, gas_field, time, find_cost):
        """
        Determines which sites are surveyed during the current time step.
        Accounts for the number of sites surveyed per timestep

        :param gas_field:
        :param time:
        :param find_cost: the find_cost array associated with the ldar program
        :return site_inds: the indexes of sites to be surveyed during this timestep.
        """
        n_sites = np.min([self.sites_per_timestep, len(self.site_queue)])
        # Determines the sites to survey based on operating envelope
        site_inds = self.choose_sites(gas_field, time, n_sites)
        find_cost[time.time_index] += len(site_inds) * self.site_cost
        return site_inds

    def detect(self, time, gas_field, emissions, find_cost):
        """
        The detection method implements a survey-based detection method model

        :param time: an object of type Time (defined in feast_classes)
        :param gas_field: an object of type GasField (defined in feast_classes)
        :param emissions: an Emissions object
        :param find_cost: an array in which to record the cost of SiteSurvey operations
        :return: None
        """
        # enforces the operating hours
        if self.check_time(time):
            site_inds = self.sites_surveyed(gas_field, time, find_cost)
            # TODO: append number of sites and time.current_time to site_survey_count
            if len(site_inds) > 0:
                detect = self.detect_prob_curve(time, gas_field, site_inds, emissions)
                # TODO: append len(detect) and time.current_time to detection_count
                # Deploy follow up action
                self.dispatch_object.action(detect, None)

    def action(self, site_inds=None, emit_inds=None):
        """
        Action to add sites to queue. Expected to be called by another detection method or by an LDAR program

        :param site_inds: List of sites to add to the queue
        :param emit_inds: Not used.
        :return: None
        """
        self.extend_site_queue(site_inds)
