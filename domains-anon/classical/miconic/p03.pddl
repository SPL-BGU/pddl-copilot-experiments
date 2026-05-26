


(define (problem mixed-f3-p2-u0-v0-d0-a0-n0-A0-B0-N0-F0)
   (:domain submersible)
   (:objects diver0 diver1 - diver
             deck0 deck1 deck2 - deck)


(:init
(shallower_than deck0 deck1)
(shallower_than deck0 deck2)

(shallower_than deck1 deck2)



(embarks_at diver0 deck0)
(disembarks_at diver0 deck2)

(embarks_at diver1 deck0)
(disembarks_at diver1 deck1)






(pod-at deck0)
)


(:goal (and
(delivered diver0)
(delivered diver1)
))
)
