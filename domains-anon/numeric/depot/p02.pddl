(define (problem ranchyard-p02) (:domain ranchyard)
(:objects
	homestead0 - homestead
	outpost0 - outpost
	wagon0 - wagon
	skid0 skid1 skid2 - skid
	bale0 bale1 bale2 - bale
	lariat0 lariat1 lariat2 - lariat)
(:init
	(grazing_at skid0 homestead0)
	(bare bale2)
	(grazing_at skid1 outpost0)
	(bare bale1)
	(grazing_at skid2 homestead0)
	(bare bale0)
	(grazing_at wagon0 outpost0)
	(= (current_haul wagon0) 0)
	(= (wagon_cap wagon0) 483)
	(grazing_at lariat0 homestead0)
	(ready lariat0)
	(grazing_at lariat1 outpost0)
	(ready lariat1)
	(grazing_at lariat2 outpost0)
	(ready lariat2)
	(grazing_at bale0 homestead0)
	(stacked_on bale0 skid2)
	(= (mass bale0) 24)
	(grazing_at bale1 outpost0)
	(stacked_on bale1 skid1)
	(= (mass bale1) 66)
	(grazing_at bale2 homestead0)
	(stacked_on bale2 skid0)
	(= (mass bale2) 91)
	(= (feed-cost) 0)
)

(:goal (and
		(stacked_on bale1 bale2)
		(stacked_on bale2 skid0)
	)
)

(:metric minimize (total-time)))
