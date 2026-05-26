

(define (problem bw_rand_3)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3 - bowl)
(:init
(hands_idle)
(on_tatami bowl1)
(set_on bowl2 bowl1)
(on_tatami bowl3)
(unstacked bowl2)
(unstacked bowl3)

    (hands_idle undef_obj_xyz))
(:goal
(and
(set_on bowl3 bowl1))
)
)
