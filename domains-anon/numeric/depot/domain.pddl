(define (domain ranchyard)
(:requirements :typing :fluents)
(:types range range_asset - object
  homestead outpost - range
        wagon lariat platform - range_asset
        skid bale - platform)

(:predicates (grazing_at ?x - range_asset ?y - range)
             (stacked_on ?x - bale ?y - platform)
             (loaded_in ?x - bale ?y - wagon)
             (hauling ?x - lariat ?y - bale)
             (ready ?x - lariat)
             (bare ?x - platform)
)

(:functions
  (wagon_cap ?t - wagon)
  (current_haul ?t - wagon)
  (mass ?c - bale)
  (feed-cost)
)

(:action mosey
:parameters (?x - wagon ?y - range ?z - range)
:precondition (and (grazing_at ?x ?y))
:effect (and (not (grazing_at ?x ?y)) (grazing_at ?x ?z)
    (increase (feed-cost) 10)))

(:action rope_up
:parameters (?x - lariat ?y - bale ?z - platform ?p - range)
:precondition (and (grazing_at ?x ?p) (ready ?x) (grazing_at ?y ?p) (stacked_on ?y ?z) (bare ?y))
:effect (and (not (grazing_at ?y ?p)) (hauling ?x ?y) (not (bare ?y)) (not (ready ?x))
             (bare ?z) (not (stacked_on ?y ?z)) (increase (feed-cost) 1)))

(:action rope_down
:parameters (?x - lariat ?y - bale ?z - platform ?p - range)
:precondition (and (grazing_at ?x ?p) (grazing_at ?z ?p) (bare ?z) (hauling ?x ?y))
:effect (and (ready ?x) (not (hauling ?x ?y)) (grazing_at ?y ?p) (not (bare ?z)) (bare ?y)
    (stacked_on ?y ?z)))

(:action wrangle_in
:parameters (?x - lariat ?y - bale ?z - wagon ?p - range)
:precondition (and (grazing_at ?x ?p) (grazing_at ?z ?p) (hauling ?x ?y)
    (<= (+ (current_haul ?z) (mass ?y)) (wagon_cap ?z)))
:effect (and (not (hauling ?x ?y)) (loaded_in ?y ?z) (ready ?x)
    (increase (current_haul ?z) (mass ?y))))

(:action wrangle_out
:parameters (?x - lariat ?y - bale ?z - wagon ?p - range)
:precondition (and (grazing_at ?x ?p) (grazing_at ?z ?p) (ready ?x) (loaded_in ?y ?z))
:effect (and (not (loaded_in ?y ?z)) (not (ready ?x)) (hauling ?x ?y)
    (decrease (current_haul ?z) (mass ?y))))

)
