;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Block grouping domain
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; A number of blocks of different colours lie on a grid-like environment.
;;; The objective is to group the blocks by colour, i.e. to have all blocks
;;; of the same color in the same cell, which is at the same time
;;; different to the cell where blocks of other colors are:
;;;
;;; forall i, j color(i) = color(j) <=> loc(i) = loc(j)
;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (domain mt-bonbon-tray)
    ;(:requirements :typing )
    (:types bonbon - object )
    (:functions
        (lane ?b - bonbon)  ;; The position of a block
        (tier ?b - bonbon)  ;;
        (max_lane)
        (min_lane)
        (max_tier)
        (min_tier)
    )

    ;; Move a block from its location to an adjacent location
    (:action slide_bonbon_up
     :parameters (?b - bonbon)
     :precondition (and (<= (+ (tier ?b)1) (max_tier) ))
     :effect (and
        (increase (tier ?b) 1)
    ))

    (:action slide_bonbon_down
     :parameters (?b - bonbon)
     :precondition (and (>= (- (tier ?b) 1) (min_tier) ))
     :effect (and
        (decrease (tier ?b) 1)
    ))

    (:action slide_bonbon_right
     :parameters (?b - bonbon)
     :precondition (and (<= (+ (lane ?b)1) (max_lane) ))
     :effect (and
        (increase (lane ?b) 1)
    ))

    (:action slide_bonbon_left
     :parameters (?b - bonbon)
     :precondition (and (>= (- (lane ?b) 1) (min_lane) ))
     :effect (and
        (decrease (lane ?b) 1)
    ))

)
