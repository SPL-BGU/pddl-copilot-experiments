(define (problem ZTRAVEL-1-2-2c)
(:domain zenotravel)
(:objects
  plane1 - aircraft
  person1 - person
  person2 - person
  city0 - city
  city1 - city
  )
(:init
  (located plane1 city0)
  (= (capacity plane1) 6000)
  (= (fuel plane1) 4000)
  (= (slow-burn plane1) 3)
  (= (fast-burn plane1) 12)
  (= (onboard plane1) 0)
  (= (zoom-limit plane1) 6)
  (located person1 city0)
  (located person2 city1)
  (= (distance city0 city0) 0)
  (= (distance city0 city1) 500)
  (= (distance city1 city0) 500)
  (= (distance city1 city1) 0)
  (= (total-fuel-used) 0)
)
(:goal (and
  (located person1 city1)
  (located person2 city0)
  ))
(:metric minimize (total-fuel-used))
)
