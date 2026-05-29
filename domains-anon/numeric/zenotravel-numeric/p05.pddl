(define (problem lunar-logistics-p05)
(:domain lunar-logistics)
(:objects
  rover1 - rover
  rover2 - rover
  crew1 - crew
  crew2 - crew
  outpost0 - outpost
  outpost1 - outpost
  )
(:init
  (stationed rover1 outpost0)
  (stationed rover2 outpost1)
  (= (hopper rover1) 5000)
  (= (regolith rover1) 3000)
  (= (idle-draw rover1) 3)
  (= (rush-draw rover1) 10)
  (= (occupants rover1) 0)
  (= (rush-cap rover1) 5)
  (= (hopper rover2) 5000)
  (= (regolith rover2) 3000)
  (= (idle-draw rover2) 3)
  (= (rush-draw rover2) 10)
  (= (occupants rover2) 0)
  (= (rush-cap rover2) 5)
  (stationed crew1 outpost0)
  (stationed crew2 outpost1)
  (= (gap outpost0 outpost0) 0)
  (= (gap outpost0 outpost1) 450)
  (= (gap outpost1 outpost0) 450)
  (= (gap outpost1 outpost1) 0)
  (= (total-regolith-spent) 0)
)
(:goal (and
  (stationed crew1 outpost1)
  (stationed crew2 outpost0)
  ))
(:metric minimize (total-regolith-spent))
)
