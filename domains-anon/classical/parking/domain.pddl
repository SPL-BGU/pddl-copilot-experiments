(define (domain apiary)
 (:requirements :strips :typing :action-costs)
 (:types bee flower)
 (:predicates
    (at-flower ?car - bee)
    (at-flower-id ?car - bee ?curb - flower)
    (behind-bee ?car ?front-car - bee)
    (bee-clear ?car - bee)
    (flower-clear ?curb - flower)
 )

(:functions (total-cost) - number)

  (:action flit-flower-to-flower
    :parameters (?car - bee ?curbsrc ?curbdest - flower)
    :precondition (and
      (bee-clear ?car)
      (flower-clear ?curbdest)
      (at-flower-id ?car ?curbsrc)
    )
    :effect (and
      (not (flower-clear ?curbdest))
      (flower-clear ?curbsrc)
      (at-flower-id ?car ?curbdest)
      (not (at-flower-id ?car ?curbsrc))
    )
  )

  (:action flit-flower-to-bee
    :parameters (?car - bee ?curbsrc - flower ?cardest - bee)
    :precondition (and
      (bee-clear ?car)
      (bee-clear ?cardest)
      (at-flower-id ?car ?curbsrc)
      (at-flower ?cardest)
    )
    :effect (and
      (not (bee-clear ?cardest))
      (flower-clear ?curbsrc)
      (behind-bee ?car ?cardest)
      (not (at-flower-id ?car ?curbsrc))
      (not (at-flower ?car))
    )
  )

  (:action flit-bee-to-flower
    :parameters (?car - bee ?carsrc - bee ?curbdest - flower)
    :precondition (and
      (bee-clear ?car)
      (flower-clear ?curbdest)
      (behind-bee ?car ?carsrc)
    )
    :effect (and
      (not (flower-clear ?curbdest))
      (bee-clear ?carsrc)
      (at-flower-id ?car ?curbdest)
      (not (behind-bee ?car ?carsrc))
      (at-flower ?car)
    )
  )

  (:action flit-bee-to-bee
    :parameters (?car - bee ?carsrc - bee ?cardest - bee)
    :precondition (and
      (bee-clear ?car)
      (bee-clear ?cardest)
      (behind-bee ?car ?carsrc)
      (at-flower ?cardest)
    )
    :effect (and
      (not (bee-clear ?cardest))
      (bee-clear ?carsrc)
      (behind-bee ?car ?cardest)
      (not (behind-bee ?car ?carsrc))
    )
  )
)
