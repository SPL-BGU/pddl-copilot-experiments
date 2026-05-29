


(define (problem submersible-n02)
   (:domain submersible)
   (:objects diver0 - diver
             deck0 deck1 - deck)


(:init
(shallower_than deck0 deck1)



(embarks_at diver0 deck0)
(disembarks_at diver0 deck1)






(pod-at deck0)

    (shallower_than undef_obj_xyz))


(:goal (and
(delivered diver0)
))
)
