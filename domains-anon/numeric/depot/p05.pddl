(define (problem ranchyard-p05) (:domain ranchyard)
(:objects
  homestead0 - homestead
  outpost0 - outpost
  wagon0 - wagon
  skid0 skid1 - skid
  bale0 bale1 - bale
  lariat0 lariat1 - lariat)
(:init
  (grazing_at skid0 homestead0)
  (bare bale0)
  (grazing_at skid1 outpost0)
  (bare bale1)
  (grazing_at wagon0 homestead0)
  (= (current_haul wagon0) 0)
  (= (wagon_cap wagon0) 100)
  (grazing_at lariat0 homestead0)
  (ready lariat0)
  (grazing_at lariat1 outpost0)
  (ready lariat1)
  (grazing_at bale0 homestead0)
  (stacked_on bale0 skid0)
  (= (mass bale0) 5)
  (grazing_at bale1 outpost0)
  (stacked_on bale1 skid1)
  (= (mass bale1) 7)
  (= (feed-cost) 0)
)

(:goal (and
    (stacked_on bale0 skid1)
  )
)

(:metric minimize (total-time)))
