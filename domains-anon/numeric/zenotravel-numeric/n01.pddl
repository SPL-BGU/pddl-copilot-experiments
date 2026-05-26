(define (problem ZTRAVEL-1-2)
(:domain lunar-logistics)
(:objects
  rover1 - rover
  crew1 - crew
  crew2 - crew
  crew3 - crew
  outpost0 - outpost
  outpost1 - outpost
  outpost2 - outpost
  )
(:init
  (stationed rover1 outpost0)
  (= (hopper rover1) 6000)
  (= (regolith rover1) 4000)
  (= (idle-draw rover1) 4)
  (= (rush-draw rover1) 15)
  (= (occupants rover1) 0)
  (= (rush-cap rover1) 8)
  (stationed crew1 outpost0)
  (stationed crew2 outpost0)
  (stationed crew3 outpost1)
  (= (gap outpost0 outpost0) 0)
  (= (gap outpost0 outpost1) 678)
  (= (gap outpost0 outpost2) 775)
  (= (gap outpost1 outpost0) 678)
  (= (gap outpost1 outpost1) 0)
  (= (gap outpost1 outpost2) 810)
  (= (gap outpost2 outpost0) 775)
  (= (gap outpost2 outpost1) 810)
  (= (gap outpost2 outpost2) 0)
  (= (total-regolith-spent) 0)

)

(:metric  minimize (total-regolith-spent) )

)
