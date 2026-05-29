


(define (problem submersible-p05)
   (:domain submersible)
   (:objects diver0 diver1 diver2 - diver
             deck0 deck1 deck2 deck3 - deck)


(:init
(shallower_than deck0 deck1)
(shallower_than deck0 deck2)
(shallower_than deck0 deck3)

(shallower_than deck1 deck2)
(shallower_than deck1 deck3)

(shallower_than deck2 deck3)



(embarks_at diver0 deck1)
(disembarks_at diver0 deck2)

(embarks_at diver1 deck1)
(disembarks_at diver1 deck2)

(embarks_at diver2 deck1)
(disembarks_at diver2 deck3)






(pod-at deck0)
)


(:goal (and
(delivered diver0)
(delivered diver1)
(delivered diver2)
))
)
