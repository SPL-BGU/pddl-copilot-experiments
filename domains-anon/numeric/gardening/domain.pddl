;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Plant watering domain - metric-ff version
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; An agent on a grid-like map aims pos watering some plants by
;;; carrying water from a tap to the plants.
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Adapted to do away with the grid (Enrico Scala & Miquel Ramirez, August 2015)
;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (domain assembly-line-constrained)
    (:types
        unit zone - object
        robot_arm workstation stock_bin - unit
    )
    ; (:predicates
    ;    (CONNECTED ?x ?y - location) ;; Whether two locations are connected.
    ;)

    (:functions
        (east_edge) ;; bounds
        (north_edge) ;; bounds
        (south_edge) ;; bounds
        (west_edge) ;; bounds
        (col ?t - unit) ;; x coordinate of the location for ?t
        (row ?t - unit) ;; y coordinate of the location for ?t
        (held_stock) ;; The amount of water carried by the agent.
        (delivered_to ?p - workstation) ;; The amount of water poured to the plant so far.
        (total_delivered) ;; The total amount of water poured so far.
        (total_drawn) ;; The total amount of water retrieved from the tap.
        (ceiling) ;; The maximum integer we consider - a static value
    )

    ;; Move an agent to a neighboring location
    (:action roll_north
        :parameters (?a - robot_arm)
        :precondition (and (<= (+ (row ?a) 1) (north_edge)))
        :effect (and
            (increase (row ?a) 1))
    )

    (:action roll_south
        :parameters (?a - robot_arm)
        :precondition (and (>= (- (row ?a) 1) (south_edge)))
        :effect (and
            (decrease (row ?a) 1))
    )

    (:action roll_east
        :parameters (?a - robot_arm)
        :precondition (and (<= (+ (col ?a) 1) (east_edge)))
        :effect (and
            (increase (col ?a) 1))
    )

    (:action roll_west
        :parameters (?a - robot_arm)
        :precondition (and (>= (- (col ?a) 1) (west_edge)))
        :effect (and
            (decrease (col ?a) 1))
    )

    (:action roll_northwest
        :parameters (?a - robot_arm)
        :precondition (and (>= (- (col ?a) 1) (west_edge)) (<= (+ (row ?a) 1) (north_edge)))
        :effect (and
            (increase (row ?a) 1) (decrease (col ?a) 1))
    )

    (:action roll_northeast
        :parameters (?a - robot_arm)
        :precondition (and (<= (+ (col ?a) 1) (east_edge)) (<= (+ (row ?a) 1) (north_edge)))
        :effect (and
            (increase (row ?a) 1) (increase (col ?a) 1))
    )

    (:action roll_southwest
        :parameters (?a - robot_arm)
        :precondition (and (>= (- (col ?a) 1) (west_edge)) (>= (- (row ?a) 1) (south_edge)))
        :effect (and
            (decrease (col ?a) 1) (decrease (row ?a) 1))
    )

    (:action roll_southeast
        :parameters (?a - robot_arm)
        :precondition (and (<= (+ (col ?a) 1) (east_edge)) (>= (- (row ?a) 1) (south_edge)))
        :effect (and
            (decrease (row ?a) 1) (increase (col ?a) 1))
    )

    ;; Load one unit of water from a tap into the agent's bucket.
    (:action draw_stock
        :parameters (?a - robot_arm ?t - stock_bin)
        :precondition (and (= (col ?a) (col ?t)) (=(row ?a) (row ?t))
            (<= (+ (total_drawn) 1) (ceiling))
            (<= (+ (held_stock) 1) (ceiling))
        )
        :effect (and (increase (held_stock) 1) (increase (total_drawn) 1))
    )

    ;; Pours one unit of water from the agent's bucket into a plant.
    (:action deliver_stock
        :parameters (?a - robot_arm ?p - workstation)
        :precondition (and (= (col ?a) (col ?p)) (=(row ?a) (row ?p))
            (>= (held_stock) 1)
            (<= (+ (total_delivered) 1) (ceiling))
            (<= (+ (delivered_to ?p) 1) (ceiling))
        )
        :effect (and
            (decrease (held_stock) 1)
            (increase (delivered_to ?p) 1)
            (increase (total_delivered) 1)
        )
    )
)
