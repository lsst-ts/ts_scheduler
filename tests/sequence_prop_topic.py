import SALPY_scheduler

seqprop = SALPY_scheduler.scheduler_sequencePropConfigC()
seqprop.name = "SequenceProposal1"
seqprop.prop_id = 1
seqprop.twilight_boundary = -18.0
seqprop.delta_lst = 60.0
seqprop.dec_window = 90.0
seqprop.max_airmass = 1.5
seqprop.max_cloud = 0.7
seqprop.min_distance_moon = 30.0
seqprop.exclude_planets = True
seqprop.num_user_regions = 4
seqprop.user_region_ids[0] = 1
seqprop.user_region_ids[1] = 20
seqprop.user_region_ids[2] = 350
seqprop.user_region_ids[3] = 4015
seqprop.num_sub_sequences = 1
seqprop.sub_sequence_names = "test1"
seqprop.num_sub_sequence_filters[0] = 5
seqprop.sub_sequence_filters = "g,r,i,z,y"
seqprop.num_sub_sequence_filter_visits[0] = 20
seqprop.num_sub_sequence_filter_visits[1] = 25
seqprop.num_sub_sequence_filter_visits[2] = 30
seqprop.num_sub_sequence_filter_visits[3] = 20
seqprop.num_sub_sequence_filter_visits[4] = 27
seqprop.num_sub_sequence_events[0] = 30
seqprop.num_sub_sequence_max_missed[0] = 2
seqprop.sub_sequence_time_intervals[0] = 5 * 24 * 3600
seqprop.sub_sequence_time_window_starts[0] = 0.0
seqprop.sub_sequence_time_window_maximums[0] = 1.0
seqprop.sub_sequence_time_window_ends[0] = 2.0
seqprop.sub_sequence_time_weights[0] = 1.0
seqprop.num_master_sub_sequences = 2
seqprop.master_sub_sequence_names = "master1,master2"
seqprop.num_nested_sub_sequences[0] = 2
seqprop.num_nested_sub_sequences[1] = 1
seqprop.nested_sub_sequence_names = "nested1,nested2,nested3"
seqprop.num_master_sub_sequence_events[0] = 20
seqprop.num_master_sub_sequence_events[1] = 15
seqprop.num_master_sub_sequence_max_missed[0] = 1
seqprop.num_master_sub_sequence_max_missed[1] = 3
seqprop.master_sub_sequence_time_intervals[0] = 648000
seqprop.master_sub_sequence_time_intervals[1] = 518400
seqprop.master_sub_sequence_time_window_starts[0] = 0.0
seqprop.master_sub_sequence_time_window_starts[1] = 0.0
seqprop.master_sub_sequence_time_window_maximums[0] = 1.0
seqprop.master_sub_sequence_time_window_maximums[1] = 1.0
seqprop.master_sub_sequence_time_window_ends[0] = 2.0
seqprop.master_sub_sequence_time_window_ends[1] = 2.0
seqprop.master_sub_sequence_time_weights[0] = 1.0
seqprop.master_sub_sequence_time_weights[1] = 1.0
seqprop.num_nested_sub_sequence_filters[0] = 3
seqprop.num_nested_sub_sequence_filters[1] = 2
seqprop.num_nested_sub_sequence_filters[2] = 2
seqprop.nested_sub_sequence_filters = "r,g,i,z,y,u,y"
seqprop.num_nested_sub_sequence_filter_visits[0] = 10
seqprop.num_nested_sub_sequence_filter_visits[1] = 10
seqprop.num_nested_sub_sequence_filter_visits[2] = 20
seqprop.num_nested_sub_sequence_filter_visits[3] = 3
seqprop.num_nested_sub_sequence_filter_visits[4] = 3
seqprop.num_nested_sub_sequence_filter_visits[5] = 5
seqprop.num_nested_sub_sequence_filter_visits[6] = 5
seqprop.num_nested_sub_sequence_events[0] = 20
seqprop.num_nested_sub_sequence_events[1] = 10
seqprop.num_nested_sub_sequence_events[2] = 15
seqprop.num_nested_sub_sequence_max_missed[0] = 1
seqprop.num_nested_sub_sequence_max_missed[1] = 1
seqprop.num_nested_sub_sequence_max_missed[2] = 5
seqprop.nested_sub_sequence_time_intervals[0] = 7200
seqprop.nested_sub_sequence_time_intervals[1] = 3600
seqprop.nested_sub_sequence_time_intervals[2] = 900
seqprop.nested_sub_sequence_time_window_starts[0] = 0.0
seqprop.nested_sub_sequence_time_window_starts[1] = 0.0
seqprop.nested_sub_sequence_time_window_starts[2] = 0.0
seqprop.nested_sub_sequence_time_window_maximums[0] = 1.0
seqprop.nested_sub_sequence_time_window_maximums[1] = 1.0
seqprop.nested_sub_sequence_time_window_maximums[2] = 1.0
seqprop.nested_sub_sequence_time_window_ends[0] = 2.0
seqprop.nested_sub_sequence_time_window_ends[1] = 2.0
seqprop.nested_sub_sequence_time_window_ends[2] = 2.0
seqprop.nested_sub_sequence_time_weights[0] = 1.0
seqprop.nested_sub_sequence_time_weights[1] = 1.0
seqprop.nested_sub_sequence_time_weights[2] = 1.0
seqprop.num_filters = 6
seqprop.filter_names = "u,g,r,i,z,y"
seqprop.bright_limit[0] = 21.0
seqprop.bright_limit[1] = 21.0
seqprop.bright_limit[2] = 21.0
seqprop.bright_limit[3] = 21.0
seqprop.bright_limit[4] = 21.0
seqprop.bright_limit[5] = 21.0
seqprop.dark_limit[0] = 30.0
seqprop.dark_limit[1] = 30.0
seqprop.dark_limit[2] = 30.0
seqprop.dark_limit[3] = 30.0
seqprop.dark_limit[4] = 30.0
seqprop.dark_limit[5] = 30.0
seqprop.max_seeing[0] = 2.0
seqprop.max_seeing[1] = 2.0
seqprop.max_seeing[2] = 2.0
seqprop.max_seeing[3] = 2.0
seqprop.max_seeing[4] = 2.0
seqprop.max_seeing[5] = 2.0
seqprop.num_filter_exposures[0] = 2
seqprop.num_filter_exposures[1] = 2
seqprop.num_filter_exposures[2] = 2
seqprop.num_filter_exposures[3] = 2
seqprop.num_filter_exposures[4] = 2
seqprop.num_filter_exposures[5] = 2
seqprop.exposures[0] = 15
seqprop.exposures[1] = 15
seqprop.exposures[2] = 15
seqprop.exposures[3] = 15
seqprop.exposures[4] = 15
seqprop.exposures[5] = 15
seqprop.exposures[6] = 15
seqprop.exposures[7] = 15
seqprop.exposures[8] = 15
seqprop.exposures[9] = 15
seqprop.exposures[10] = 15
seqprop.exposures[11] = 15
seqprop.max_num_targets = 100
seqprop.accept_serendipity = False
seqprop.accept_consecutive_visits = True
seqprop.restart_lost_sequences = True
seqprop.restart_complete_sequences = False
seqprop.airmass_bonus = 0.5
seqprop.hour_angle_bonus = 0.5
seqprop.hour_angle_max = 5.0
