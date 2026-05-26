;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem tankyard-p05)
	(:domain tankyard)
	(:objects
		tank0 tank1 tank2 - tank
	)
  (:init
		(= (level tank0) 20)
	(= (level tank1) 88)
	(= (level tank2) 34)

        (= (flowrate tank0) 0)
	(= (flowrate tank1) 0)
	(= (flowrate tank2) 0)

		(= (capacity) 100)
	)
	(:goal
		(and
			(<= (+ (level tank0) 1) (level tank1))
	(<= (+ (level tank1) 1) (level tank2))
		)
	)
)

