(define (problem depot_min) (:domain depot)
(:objects
  depot0 - depot
  distributor0 - distributor
  truck0 - truck
  pallet0 pallet1 - pallet
  crate0 crate1 - crate
  hoist0 hoist1 - hoist)
(:init
  (at pallet0 depot0)
  (clear crate0)
  (at pallet1 distributor0)
  (clear crate1)
  (at truck0 depot0)
  (= (current_load truck0) 0)
  (= (load_limit truck0) 100)
  (at hoist0 depot0)
  (available hoist0)
  (at hoist1 distributor0)
  (available hoist1)
  (at crate0 depot0)
  (on crate0 pallet0)
  (= (weight crate0) 5)
  (at crate1 distributor0)
  (on crate1 pallet1)
  (= (weight crate1) 7)
  (= (fuel-cost) 0)
)

(:goal (and
    (on crate0 pallet1)
  )
)

(:metric minimize (total-time)))
