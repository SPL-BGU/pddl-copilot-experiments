

(define (problem tearoom-n05)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3 - bowl)
(:init
(hands_idle)
(on_tatami bowl1)
(set_on bowl2 bowl1)
(on_tatami bowl3)
(unstacked bowl2)
(unstacked bowl3)
)

))
