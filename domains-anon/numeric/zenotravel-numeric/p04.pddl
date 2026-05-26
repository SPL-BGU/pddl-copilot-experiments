(define (problem ZTRAVEL-1-2-3c)
(:domain lunar-logistics)
(:objects
  rover1 - rover
  crew1 - crew
  crew2 - crew
  outpost0 - outpost
  outpost1 - outpost
  outpost2 - outpost
  )
(:init
  (stationed rover1 outpost0)
  (= (hopper rover1) 7000)
  (= (regolith rover1) 5000)
  (= (idle-draw rover1) 4)
  (= (rush-draw rover1) 12)
  (= (occupants rover1) 0)
  (= (rush-cap rover1) 6)
  (stationed crew1 outpost0)
  (stationed crew2 outpost1)
  (= (gap outpost0 outpost0) 0)
  (= (gap outpost0 outpost1) 600)
  (= (gap outpost0 outpost2) 700)
  (= (gap outpost1 outpost0) 600)
  (= (gap outpost1 outpost1) 0)
  (= (gap outpost1 outpost2) 500)
  (= (gap outpost2 outpost0) 700)
  (= (gap outpost2 outpost1) 500)
  (= (gap outpost2 outpost2) 0)
  (= (total-regolith-spent) 0)
)
(:goal (and
  (stationed crew1 outpost2)
  (stationed crew2 outpost0)
  ))
(:metric minimize (total-regolith-spent))
)
