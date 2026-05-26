(define (problem ZTRAVEL-1-2-2c)
(:domain lunar-logistics)
(:objects
  rover1 - rover
  crew1 - crew
  crew2 - crew
  outpost0 - outpost
  outpost1 - outpost
  )
(:init
  (stationed rover1 outpost0)
  (= (hopper rover1) 6000)
  (= (regolith rover1) 4000)
  (= (idle-draw rover1) 3)
  (= (rush-draw rover1) 12)
  (= (occupants rover1) 0)
  (= (rush-cap rover1) 6)
  (stationed crew1 outpost0)
  (stationed crew2 outpost1)
  (= (gap outpost0 outpost0) 0)
  (= (gap outpost0 outpost1) 500)
  (= (gap outpost1 outpost0) 500)
  (= (gap outpost1 outpost1) 0)
  (= (total-regolith-spent) 0)
)
(:goal (and
  (stationed crew1 outpost1)
  (stationed crew2 outpost0)
  ))
(:metric minimize (total-regolith-spent))
)
