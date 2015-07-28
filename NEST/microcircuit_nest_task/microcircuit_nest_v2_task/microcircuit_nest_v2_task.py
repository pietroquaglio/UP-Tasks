#!/usr/bin/env python
from active_worker.task import task
import yaml
import matplotlib
matplotlib.use('Agg')
import time
# import glob
from task_types import TaskTypes as tt

# The simulation runs with values defined in config-file microcircuit.yaml
#
# NOTE: according to an incompatibility with Python2.6, NEST2.6.0 and PyNN0.7.5
# , connections to spike detectors and voltmeters are here established with
# PyNEST instead of PyNN. respective code is marked with "PYTHON2.6:"
# and can be changed back in future versions.


@task
def microcircuit_nest_v2_task(config_file):
    '''
        Task Manifest Version: 1
        Full Name: microcircuit_nest_task
        Caption: Microcircuit model
        Author: NEST_Developer and Contributors
        Description: |
            Microcircuit model
        Categories:
            - NEST
        Compatible_queues: ['cscs_viz', 'cscs_bgq', 'epfl_viz']
        Accepts:
            config_file: application/vnd.juelich.simulation.config
        Returns:
            res: application/vnd.juelich.bundle.nest.data
    '''

    # load config of microcircuit_model .yaml
    cfile = microcircuit_nest_v2_task.task.uri.get_file(config_file)
    with open(cfile, 'r') as f:
        conf = yaml.load(f)


    plot_filename = 'spiking_activity.png'

    # create bundle & export bundle, THIS SHOULD BE MIMETYPE of INM-6
    my_bundle_mimetype = "application/vnd.juelich.bundle.nest.data"
    bundle = microcircuit_nest_v2_task.task.uri.build_bundle(my_bundle_mimetype)

    results = _run_microcircuit(plot_filename, conf)

    # print bundle
    print "results = ", results

    for file_name, file_mimetype in results:
        bundle.add_file(src_path=file_name,
                        dst_path=file_name,
                        bundle_path=file_name,
                        mime_type=file_mimetype)

    my_bundle_name = 'microcircuit_model_bundle'
    return bundle.save(my_bundle_name)


def _run_microcircuit(plot_filename, conf):
    from Init_microcircuit import Init_microcircuit
    mc = Init_microcircuit(conf)

    # import sys

    # sys.path.append(mc.properties['system_params']['backend_path'])
    # sys.path.append(mc.properties['system_params']['pyNN_path'])

    simulator = mc.properties['simulator']

    import logging

    # prepare simulation
    logging.basicConfig()
    import pyNN.nest as sim
    master_seed = mc.properties['params_dict']['nest']['master_seed']
    layers = mc.properties['layers']
    pops = mc.properties['pops']
    # record_v = mc.properties['params_dict']['nest']['record_v']
    # record_corr = mc.properties['params_dict']['nest']['record_corr']
    # tau_max = mc.properties['tau_max']
    plot_spiking_activity = mc.properties['plot_spiking_activity']
    raster_t_min = mc.properties['raster_t_min']
    raster_t_max = mc.properties['raster_t_max']
    # frac_to_plot = conf['frac_to_plot']
    # record_fraction = mc.properties['params_dict']['nest']['record_fraction']
    # N_scaling = mc.properties['params_dict']['nest']['N_scaling']
    # frac_record_spikes = mc.properties['params_dict']['nest']['frac_record_spikes']
    # n_record = mc.properties['params_dict']['nest']['n_record']

    # Numbers of neurons from which to record spikes
    n_rec = mc.get_n_rec()

    sim.setup(**conf['simulator_params'][simulator])

    if simulator == 'nest':
        n_vp = sim.nest.GetKernelStatus('total_num_virtual_procs')
        if sim.rank() == 0:
            print 'n_vp: ', n_vp
            print 'master_seed: ', master_seed
        sim.nest.SetKernelStatus({'print_time': False,
                                  'dict_miss_is_error': False,
                                  'grng_seed': master_seed,
                                  'rng_seeds': range(master_seed + 1,
                                                     master_seed + n_vp + 1),
                                  # PYTHON2.6: FOR WRITING OUTPUT FROM RECORDING
                                  # DEVICES WITH PYNEST FUNCTIONS, THE OUTPUT PATH
                                  # IS NOT AUTOMATICALLY THE CWD BUT HAS TO BE SET
                                  # MANUALLY
                                  'data_path': conf['system_params']['output_path']})

    import network

    # result of export-files
    results = []

    # create network
    start_netw = time.time()
    n = network.Network(sim)
    device_list = n.setup(sim, conf)
    end_netw = time.time()
    if sim.rank() == 0:
        print 'Creating the network took ', end_netw - start_netw, ' s'
        print "Simulating..."

    start_sim = time.time()
    sim.run(conf['simulator_params'][simulator]['sim_duration'])
    end_sim = time.time()
    if sim.rank() == 0:
        print 'Simulation took ', end_sim - start_sim, ' s'

    # print device_list
    for sd in device_list:
        fname_export = sim.nest.GetStatus(sd)[0]['filenames'][0]
        filename = fname_export.split('/')[-1]
        res = (filename, 'application/vnd.juelich.bundle.nest.data')
        results.append(res)

    end_results = _export_data(layers, pops, conf, n, plot_spiking_activity,
                               raster_t_min, raster_t_max, sim, n_rec,
                               plot_filename, results)
    return end_results


def _export_data(layers, pops, conf, n, plot_spiking_activity, raster_t_min,
                 raster_t_max, sim, n_rec, plot_filename, results):
    from plotting import Plotting
    frac_to_plot = conf['frac_to_plot']

    start_writing = time.time()


    # PYTHON2.6: SPIKE AND VOLTAGE FILES ARE CURRENTLY WRITTEN WHEN A SPIKE DETECTOR
    # OR A VOLTMETER IS CONNECTED WITH 'to_file': True
    for output in ['spikes_', 'voltages_']:
        filestart = conf['system_params']['output_path'] + output + '*'
        print "filestart = ", filestart

        # filelist = glob.glob(filestart)
        # results.extend(filelist)  # TODO adapt to bundle framework

    # print "filelist = ", filelist  # filelist is empty

    # for layer in layers:
    #     for pop in pops:
    #         # filename = conf['system_params']['output_path'] + '/spikes_' + layer + pop + '.dat'
    #         filename = conf['system_params']['output_path'] + 'spikes_' + layer + pop + '.dat'
    #         n.pops[layer][pop].printSpikes(filename, gather=False)

    #         # add filename and filepath into results
    #         subres = (filename, 'application/vnd.juelich.bundle.nest.data')
    #         results.append(subres)

    # if record_v:
    #     for layer in layers:
    #         for pop in pops:
    #             filename = conf['system_params']['output_path'] + '/voltages_' + layer + pop + '.dat'
    #             n.pops[layer][pop].print_v(filename, gather=False)

    # if record_corr and simulator == 'nest':
    #     if sim.nest.GetStatus(n.corr_detector, 'local')[0]:
    #         print 'getting count_covariance on rank ', sim.rank()
    #         cov_all = sim.nest.GetStatus(n.corr_detector, 'count_covariance')[0]
    #         delta_tau = sim.nest.GetStatus(n.corr_detector, 'delta_tau')[0]

    #         cov = {}
    #         for target_layer in np.sort(layers.keys()):
    #             for target_pop in pops:
    #                 target_index = conf['structure'][target_layer][target_pop]
    #                 cov[target_index] = {}
    #                 for source_layer in np.sort(layers.keys()):
    #                     for source_pop in pops:
    #                         source_index = conf['structure'][source_layer][source_pop]
    #                         cov[target_index][source_index] = np.array(list(cov_all[target_index][source_index][::-1]) \
    #                         + list(cov_all[source_index][target_index][1:]))

    #         f = open(conf['system_params']['output_path'] + '/covariances.dat', 'w')
    #         print >>f, 'tau_max: ', tau_max
    #         print >>f, 'delta_tau: ', delta_tau
    #         print >>f, 'simtime: ', conf['simulator_params'][simulator]['sim_duration'], '\n'

    #         for target_layer in np.sort(layers.keys()):
    #             for target_pop in pops:
    #                 target_index = conf['structure'][target_layer][target_pop]
    #                 for source_layer in np.sort(layers.keys()):
    #                     for source_pop in pops:
    #                         source_index = conf['structure'][source_layer][source_pop]
    #                         print >>f, target_layer, target_pop, '-', source_layer, source_pop
    #                         print >>f, 'n_events_target: ', sim.nest.GetStatus(n.corr_detector, 'n_events')[0][target_index]
    #                         print >>f, 'n_events_source: ', sim.nest.GetStatus(n.corr_detector, 'n_events')[0][source_index]
    #                         for i in xrange(len(cov[target_index][source_index])):
    #                             print >>f, cov[target_index][source_index][i]
    #                         print >>f, ''
    #         f.close()

    end_writing = time.time()
    print "Writing data took ", end_writing - start_writing, " s"

    if plot_spiking_activity and sim.rank() == 0:
        complett_result = Plotting.plot_raster_bars(raster_t_min, raster_t_max,
                                                    n_rec, frac_to_plot, n.pops,
                                                    conf['system_params']['output_path'],
                                                    plot_filename, results, conf)

    sim.end()

    return complett_result

if __name__ == '__main__':
    config_file = 'microcircuit.yaml'
    filename = tt.URI('application/vnd.juelich.simulation.config', config_file)
    microcircuit_nest_v2_task(filename)
