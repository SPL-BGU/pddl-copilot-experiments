
(define (domain orbital)

    (:requirements :typing :fluents)

    (:types
        module - object
    )

    (:predicates
        (linked ?f1 - module ?f2 - module)
    )

    (:functions
        (oxygen ?b - module)
        (power_drain)
    )

    ;; Move a person from a unit f1 to a unit f2
    (:action vent-fast
        :parameters (?f1 - module ?f2 - module)
        :precondition (and (>= (oxygen ?f1) 4) (linked ?f1 ?f2))
        :effect (and(decrease (oxygen ?f1) 4) (increase (oxygen ?f2) 2) (increase (power_drain) 1) (visited ?f2))
    )

    (:action vent-slow
        :parameters (?f1 - module ?f2 - module)
        :precondition (and (>= (oxygen ?f1) 1) (linked ?f1 ?f2))
        :effect (and(decrease (oxygen ?f1) 1) (increase (oxygen ?f2) 1))
    )

)
