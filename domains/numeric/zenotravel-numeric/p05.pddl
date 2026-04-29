(define (problem ZTRAVEL-2-2-2c)
(:domain zenotravel)
(:objects
	plane1 - aircraft
	plane2 - aircraft
	person1 - person
	person2 - person
	city0 - city
	city1 - city
	)
(:init
	(located plane1 city0)
	(located plane2 city1)
	(= (capacity plane1) 5000)
	(= (fuel plane1) 3000)
	(= (slow-burn plane1) 3)
	(= (fast-burn plane1) 10)
	(= (onboard plane1) 0)
	(= (zoom-limit plane1) 5)
	(= (capacity plane2) 5000)
	(= (fuel plane2) 3000)
	(= (slow-burn plane2) 3)
	(= (fast-burn plane2) 10)
	(= (onboard plane2) 0)
	(= (zoom-limit plane2) 5)
	(located person1 city0)
	(located person2 city1)
	(= (distance city0 city0) 0)
	(= (distance city0 city1) 450)
	(= (distance city1 city0) 450)
	(= (distance city1 city1) 0)
	(= (total-fuel-used) 0)
)
(:goal (and
	(located person1 city1)
	(located person2 city0)
	))
(:metric minimize (total-fuel-used))
)
