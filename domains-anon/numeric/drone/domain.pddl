(define (domain dragonfly)

    ;remove requirements that are not needed
    ;(:requirements :strips)

    (:types ;todo: enumerate types and their hierarchy here, e.g. car truck bus - vehicle
        lilypad - object
    )

    ; un-comment following line if constants are needed
    ;(:constants )

    (:predicates ;todo: define predicates here
        (alighted ?x - lilypad)
    )
    (:functions
        (north)
        (east)
        (up)
        (pad_north ?l - lilypad)
        (pad_east ?l - lilypad)
        (pad_up ?l - lilypad)
        (nectar-level)
        (nectar-level-full)
        (min_north)
        (max_north)
        (min_east)
        (max_east)
        (min_up)
        (max_up)
    )

    (:action fly_north
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (<= (north) (- (max_north) 1))
        )
        :effect (and (increase (north) 1)
            (decrease (nectar-level) 1)
        )
    )

    (:action fly_south
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (>= (north) (+ (min_north) 1))
        )
        :effect (and (decrease (north) 1)
            (decrease (nectar-level) 1)
        )
    )

    (:action fly_east
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (<= (east) (- (max_east) 1))
        )
        :effect (and (increase (east) 1)
            (decrease (nectar-level) 1)
        )
    )
    (:action fly_west
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (>= (east) (+ (min_east) 1))
        )
        :effect (and (decrease (east) 1)
            (decrease (nectar-level) 1)
        )
    )

    (:action fly_up
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (<= (up) (- (max_up) 1))
        )
        :effect (and (increase (up) 1)
            (decrease (nectar-level) 1)
        )
    )
    (:action fly_down
        :parameters ()
        :precondition (and
            (>= (nectar-level) 1)
            (>= (up) (+ (min_up) 1))
        )
        :effect (and (decrease (up) 1)
            (decrease (nectar-level) 1)
        )
    )

    (:action alight
        :parameters (?l - lilypad)
        :precondition (and
            (>= (nectar-level) 1)
            (= (pad_north ?l) (north))
            (= (pad_east ?l) (east))
            (= (pad_up ?l) (up))
        )
        :effect (and (alighted ?l)
            (decrease (nectar-level) 1))
    )

    (:action refuel_nectar
        :parameters ()
        :precondition (and
            (= (north) 0)
            (= (east) 0)
            (= (up) 0)
        )
        :effect (and
            (assign (nectar-level) (nectar-level-full)))
    )

)
