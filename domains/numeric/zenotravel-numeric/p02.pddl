(define (problem ZTRAVEL-1-1-2c)
(:domain zenotravel)
(:objects
	plane1 - aircraft
	person1 - person
	city0 - city
	city1 - city
	)
(:init
	(located plane1 city0)
	(= (capacity plane1) 5000)
	(= (fuel plane1) 3000)
	(= (slow-burn plane1) 3)
	(= (fast-burn plane1) 10)
	(= (onboard plane1) 0)
	(= (zoom-limit plane1) 5)
	(located person1 city0)
	(= (distance city0 city0) 0)
	(= (distance city0 city1) 400)
	(= (distance city1 city0) 400)
	(= (distance city1 city1) 0)
	(= (total-fuel-used) 0)
)
(:goal (and
	(located person1 city1)
	))
(:metric minimize (total-fuel-used))
)
