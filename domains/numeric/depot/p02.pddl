(define (problem depotprob5656) (:domain depot)
(:objects
	depot0 - depot
	distributor0 - distributor
	truck0 - truck
	pallet0 pallet1 pallet2 - pallet
	crate0 crate1 crate2 - crate
	hoist0 hoist1 hoist2 - hoist)
(:init
	(at pallet0 depot0)
	(clear crate2)
	(at pallet1 distributor0)
	(clear crate1)
	(at pallet2 depot0)
	(clear crate0)
	(at truck0 distributor0)
	(= (current_load truck0) 0)
	(= (load_limit truck0) 483)
	(at hoist0 depot0)
	(available hoist0)
	(at hoist1 distributor0)
	(available hoist1)
	(at hoist2 distributor0)
	(available hoist2)
	(at crate0 depot0)
	(on crate0 pallet2)
	(= (weight crate0) 24)
	(at crate1 distributor0)
	(on crate1 pallet1)
	(= (weight crate1) 66)
	(at crate2 depot0)
	(on crate2 pallet0)
	(= (weight crate2) 91)
	(= (fuel-cost) 0)
)

(:goal (and
		(on crate1 crate2)
		(on crate2 pallet0)
	)
)

(:metric minimize (total-time)))
