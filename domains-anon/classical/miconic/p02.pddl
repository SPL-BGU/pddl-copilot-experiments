


(define (problem mixed-f2-p2-u0-v0-d0-a0-n0-A0-B0-N0-F0)
   (:domain submersible)
   (:objects diver0 diver1 - diver
             deck0 deck1 - deck)


(:init
(shallower_than deck0 deck1)



(embarks_at diver0 deck1)
(disembarks_at diver0 deck0)

(embarks_at diver1 deck1)
(disembarks_at diver1 deck0)






(pod-at deck0)
)


(:goal (and
(delivered diver0)
(delivered diver1)
))
)
