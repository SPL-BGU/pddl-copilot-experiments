(define (problem ranchyard-p03) (:domain ranchyard)
(:objects
	homestead0 - homestead
	outpost0 outpost1 - outpost
	wagon0 wagon1 - wagon
	skid0 skid1 skid2 - skid
	bale0 bale1 bale2 - bale
	lariat0 lariat1 lariat2 - lariat)
(:init
	(grazing_at skid0 homestead0)
	(bare bale1)
	(grazing_at skid1 outpost0)
	(bare skid1)
	(grazing_at skid2 outpost1)
	(bare bale2)
	(grazing_at wagon0 outpost1)
	(= (current_haul wagon0) 0)
	(= (wagon_cap wagon0) 295)
	(grazing_at wagon1 homestead0)
	(= (current_haul wagon1) 0)
	(= (wagon_cap wagon1) 268)
	(grazing_at lariat0 homestead0)
	(ready lariat0)
	(grazing_at lariat1 outpost0)
	(ready lariat1)
	(grazing_at lariat2 outpost1)
	(ready lariat2)
	(grazing_at bale0 outpost1)
	(stacked_on bale0 skid2)
	(= (mass bale0) 89)
	(grazing_at bale1 homestead0)
	(stacked_on bale1 skid0)
	(= (mass bale1) 62)
	(grazing_at bale2 outpost1)
	(stacked_on bale2 bale0)
	(= (mass bale2) 42)
	(= (feed-cost) 0)
)

(:goal (and
		(stacked_on bale0 bale1)
		(stacked_on bale1 skid1)
		(stacked_on bale2 skid2)
	)
)

(:metric minimize (total-time)))
