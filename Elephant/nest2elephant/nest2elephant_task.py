#! /usr/bin/env python
import quantities as pq
import neo
from active_worker.task import task


@task
def nest2elephant_task(input_filename, t_start, t_stop, gdf_id_list):
    '''
        Task Manifest Version: 1
        Full Name: nest2elephant_task
        Caption: nest2elephant
        Author: Jakob Jordan
        Description: |
            Takes a gdf file generated by NEST and converts it into a neo
            hdf5 file, that can be processed by Elephant.
        Categories:
            - FDAT
        Compatible_queues: ['cscs_viz', 'cscs_bgq', 'epfl_viz']
        Accepts:
            input_file:
                type: application/vnd.juelich.nest.spike_times
                description: Input file that contains spiking data from a
                NEST simulation in gdf format.
            t_start:
                type: double
                description: Start time of spike train recording.
            t_stop:
                type: double
                description: Stop time of spike train recording.
            gdf_id_list:
                type: list(long)
                description: Neuron IDs in the input file that should be
                extracted. Provide an empty list to extract all neurons
                with at least one spike.
        Returns:
            res: application/unknown
    '''

    input_file = neo.io.GdfIO(input_filename)
    seg = input_file.read_segment(gdf_id_list=gdf_id_list, t_start=t_start*pq.ms, t_stop=t_stop*pq.ms)
    output_filename = input_filename.split('.')[0] + '.h5'
    output_file = neo.io.NeoHdf5IO(output_filename)
    output_file.write(seg.spiketrains)

    return nest2elephant_task.task.uri.save_file(mime_type='application/unknown', src_path=output_filename, dst_path=output_filename)


if __name__ == '__main__':
    input_filename = 'collected_spikes_L6I-296.gdf'
    t_start = 0.
    t_stop = 300.
    gdf_id_list = []
    nest2elephant_task(input_filename, t_start, t_stop, gdf_id_list)