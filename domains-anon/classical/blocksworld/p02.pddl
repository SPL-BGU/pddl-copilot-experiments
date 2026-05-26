

(define (problem tearoom-p02)
(:domain tearoom)
(:objects bowl1 bowl2 bowl3  - bowl)
(:init
(hands_idle)
(on_tatami bowl1)
(on_tatami bowl2)
(on_tatami bowl3)
(unstacked bowl1)
(unstacked bowl2)
(unstacked bowl3)
)
(:goal
(and
(set_on bowl3 bowl2))
)
)


