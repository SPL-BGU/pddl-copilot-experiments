; PolyCraft advanced domain

(define (domain ceramicsstudio)

    (:requirements :strips :typing :negative-preconditions :fluents :disjunctive-preconditions)

    (:types
        tile - object
    )

    (:constants
        kiln_block - tile
    )

    (:predicates
        (standing_on ?c - tile)

        ; Map
        (clay_tile ?c - tile)
        (empty_tile ?c - tile)
        (kiln_tile ?c - tile)
        (have_fired_vase)
    )

    (:functions
        ; Items
        (count_raw_clay_on_shelf)
        (count_wedged_clay_on_shelf)
        (count_coils_on_shelf)
        (count_glaze_jar_on_shelf)
        (count_bisque_mold_on_shelf)
    )

    ; Actions
    (:action walk_to
        :parameters (?from - tile ?to - tile)
        :precondition (and
            (standing_on ?from)
        )
        :effect (and
            (not (standing_on ?from))
            (standing_on ?to)
        )
    )

    (:action dig_clay
        :parameters (?pos - tile)
        :precondition (and
            (standing_on ?pos)
            (clay_tile ?pos)
        )
        :effect (and
            (not (clay_tile ?pos))
            (empty_tile ?pos)
            (increase (count_raw_clay_on_shelf) 1)
        )
    )

    (:action wedge_clay
        :parameters ()
        :precondition (and
            (>= (count_raw_clay_on_shelf) 1)
        )
        :effect (and
            (decrease (count_raw_clay_on_shelf) 1)
            (increase (count_wedged_clay_on_shelf) 4)
        )
    )

    (:action roll_coil
        :parameters ()
        :precondition (and
            (>= (count_wedged_clay_on_shelf) 2)
        )
        :effect (and
            (decrease (count_wedged_clay_on_shelf) 2)
            (increase (count_coils_on_shelf) 4)
        )
    )

    (:action shape_bisque_mold
        :parameters (?pos - tile)
        :precondition (and
            (standing_on ?pos)
            (not (standing_on kiln_block))
            (>= (count_wedged_clay_on_shelf) 5)
            (>= (count_coils_on_shelf) 1)
        )
        :effect (and
            (not (standing_on ?pos))
            (standing_on kiln_block)
            (decrease (count_wedged_clay_on_shelf) 5)
            (decrease (count_coils_on_shelf) 1)
            (increase (count_bisque_mold_on_shelf) 1)
        )
    )

    (:action throw_vase
        :parameters (?pos - tile)
        :precondition (and
            (standing_on ?pos)
            (not (standing_on kiln_block))
            (>= (count_wedged_clay_on_shelf) 2)
            (>= (count_coils_on_shelf) 4)
            (>= (count_glaze_jar_on_shelf) 1)
        )
        :effect (and
            (not (standing_on ?pos))
            (standing_on kiln_block)
            (decrease (count_wedged_clay_on_shelf) 2)
            (decrease (count_coils_on_shelf) 4)
            (decrease
                (count_glaze_jar_on_shelf)
                1)
            (have_fired_vase)
        )
    )

    (:action apply_glaze
        :parameters (?pos - tile)
        :precondition (and
            (standing_on ?pos)
            (clay_tile ?pos)
            (>= (count_bisque_mold_on_shelf) 1)
        )
        :effect (and
            (increase
                (count_glaze_jar_on_shelf)
                1)
        )
    )

)
