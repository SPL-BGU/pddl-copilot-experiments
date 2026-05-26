(define (problem roverprob511) (:domain arable-farm)
(:objects
  homestead - silo
  golden prime_grade bulk_grade - variety
  tractor0 - tractor
  tractor0hopper - hopper
  field0 field1 field2 - field
  gauge0 - gauge
  plot0 - plot
  )
(:init
  (reachable field0 field1)
  (reachable field1 field0)
  (reachable field1 field2)
  (reachable field2 field1)
  (reachable field2 field0)
  (reachable field0 field2)
  (has_root_clump field1)
  (has_seed_clump field2)
  (has_root_clump field2)
  (anchored_at homestead field2)
  (relay_open homestead)
  (ploughing tractor0 field1)
  (ready tractor0)
  (hopper_of tractor0hopper tractor0)
  (unfilled tractor0hopper)
  (fitted_for_seed_sampling tractor0)
  (fitted_for_gauging tractor0)
  (can_furrow tractor0 field1 field0)
  (can_furrow tractor0 field0 field1)
  (can_furrow tractor0 field1 field2)
  (can_furrow tractor0 field2 field1)
  (mounted_on gauge0 tractor0)
  (tuning_plot gauge0 plot0)
  (handles gauge0 golden)
  (handles gauge0 prime_grade)
  (handles gauge0 bulk_grade)
  (reachable_from plot0 field0)
)

(:goal (and
(undef_pred_xyz field2)
(reported_reading_data plot0 bulk_grade)
(reported_reading_data plot0 golden)
  )
)
)
