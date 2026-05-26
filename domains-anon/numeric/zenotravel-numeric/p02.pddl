(define (problem ZTRAVEL-1-1-2c)
(:domain lunar-logistics)
(:objects
  rover1 - rover
  crew1 - crew
  outpost0 - outpost
  outpost1 - outpost
  )
(:init
  (stationed rover1 outpost0)
  (= (hopper rover1) 5000)
  (= (regolith rover1) 3000)
  (= (idle-draw rover1) 3)
  (= (rush-draw rover1) 10)
  (= (occupants rover1) 0)
  (= (rush-cap rover1) 5)
  (stationed crew1 outpost0)
  (= (gap outpost0 outpost0) 0)
  (= (gap outpost0 outpost1) 400)
  (= (gap outpost1 outpost0) 400)
  (= (gap outpost1 outpost1) 0)
  (= (total-regolith-spent) 0)
)
(:goal (and
  (stationed crew1 outpost1)
  ))
(:metric minimize (total-regolith-spent))
)
