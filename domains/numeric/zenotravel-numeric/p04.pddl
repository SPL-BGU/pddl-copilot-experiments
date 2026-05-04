(define (problem ZTRAVEL-1-2-3c)
(:domain zenotravel)
(:objects
  plane1 - aircraft
  person1 - person
  person2 - person
  city0 - city
  city1 - city
  city2 - city
  )
(:init
  (located plane1 city0)
  (= (capacity plane1) 7000)
  (= (fuel plane1) 5000)
  (= (slow-burn plane1) 4)
  (= (fast-burn plane1) 12)
  (= (onboard plane1) 0)
  (= (zoom-limit plane1) 6)
  (located person1 city0)
  (located person2 city1)
  (= (distance city0 city0) 0)
  (= (distance city0 city1) 600)
  (= (distance city0 city2) 700)
  (= (distance city1 city0) 600)
  (= (distance city1 city1) 0)
  (= (distance city1 city2) 500)
  (= (distance city2 city0) 700)
  (= (distance city2 city1) 500)
  (= (distance city2 city2) 0)
  (= (total-fuel-used) 0)
)
(:goal (and
  (located person1 city2)
  (located person2 city0)
  ))
(:metric minimize (total-fuel-used))
)
