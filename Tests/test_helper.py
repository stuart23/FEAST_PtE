import numpy as np
import feast
from feast.GeneralClassesFunctions import simulation_classes as sc
import feast.GeneralClassesFunctions.emission_class_functions as lcf
import feast.GeneralClassesFunctions.results_analysis_functions as raf
from feast import DetectionModules as Dm
import os
import pickle


def basic_gas_field():
    np.random.seed(0)
    n_sites = 100
    site_dict = {}
    comp_fug = sc.Component(
        name='Fugitive emitters',
        emission_data_path='production_emissions.p',
        emission_per_comp=0.0026,
        emission_production_rate=5.4 / 650 / 365
    )
    basicpad = feast.GeneralClassesFunctions.simulation_classes.Site(
        # Simulates two wells, one tank, total components=11302
        name='basic pad',
        comp_dict={
            'Fugitive': {'number': 100, 'parameters': comp_fug},
        }
    )
    site_dict['basic pad'] = {'number': n_sites, 'parameters': basicpad}
    timeobj = feast.GeneralClassesFunctions.simulation_classes.Time(delta_t=1, end_time=2)
    initial_leaks = feast.GeneralClassesFunctions.emission_class_functions.Emission(
        flux=np.ones(100), site_index=np.random.randint(0, n_sites, 100),
        comp_index=np.random.randint(0, 100, 100), endtime=np.infty, repair_cost=np.ones(100) * 2
    )
    gas_field = feast.GeneralClassesFunctions.simulation_classes.GasField(
        sites=site_dict,
        time=timeobj,
        initial_emissions=initial_leaks
    )
    return gas_field


def ex_prob_detect_arrays():
    """
    returns an example 2D array of detection probabilities for testing purposes
    :return:
    """
    x = np.array([0.01, 0.05, 0.1, 0.5, 1, 5])
    y = np.linspace(1, 10, 10)
    x, y = np.meshgrid(x, y)
    x = np.ndarray.flatten(x)
    y = np.ndarray.flatten(y)
    xy = np.transpose(np.array([x, y]))
    prob_detect = (0.5 + 0.5 * np.array([np.math.erf((xy[ind, 0] - 0.7) / (1 * np.sqrt(2))) for ind
                                         in range(xy.shape[0])])) * (11 - y) / 10
    return xy, prob_detect
