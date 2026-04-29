(define (problem ZTRAVEL-2-1)
(:domain zeno-travel)

(:init
	(at plane1 city0)
	(fuel-level plane1 fl1)
	(at plane2 city0)
	(fuel-level plane2 fl6)
	(at person1 city1)
	(next fl0 fl1)
	(next fl1 fl2)
	(next fl2 fl3)
	(next fl3 fl4)
	(next fl4 fl5)
	(next fl5 fl6)
)
(:goal (and
	(at person1 city0)
	))

)
