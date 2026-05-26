;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (domain ballooning)
     (:requirements :typing :fluents)
     (:types
          balloon passenger - object
     )
     (:predicates
          (rescued ?t - passenger)
     )
     (:functions
          (col ?b - balloon)
          (row ?b - balloon)
          (band ?t - passenger)
     )
     ;; Increment the value in the given counter by one
     (:action drift_northeast
          :parameters (?b - balloon)
          :precondition (and)
          :effect (and(increase (col ?b) 1.5) (increase (row ?b) 1.5))
     )
     (:action drift_northwest
          :parameters (?b - balloon)
          :precondition (and)
          :effect (and(decrease (col ?b) 1.5) (increase (row ?b) 1.5))
     )
     (:action drift_east
          :parameters (?b - balloon)
          :precondition (and)
          :effect (and(increase (col ?b) 3))
     )
     (:action drift_west
          :parameters (?b - balloon)
          :precondition (and)
          :effect (and(decrease (col ?b) 3))
     )
     (:action drift_southwest
          :parameters(?b - balloon)
          :precondition (and)
          :effect (and(increase (col ?b) 2) (decrease (row ?b) 2))
     )
     (:action drift_southeast
          :parameters(?b - balloon)
          :precondition (and)
          :effect (and(decrease (col ?b) 2) (decrease (row ?b) 2))
     )
     (:action drift_south
          :parameters(?b - balloon)
          :precondition (and)
          :effect (and (decrease (row ?b) 2))
     )
     (:action rescue_passenger
          :parameters(?b - balloon ?t - passenger)
          :precondition ( and (>= (+ (col ?b) (row ?b)) (band ?t))
               (>= (- (row ?b) (col ?b)) (band ?t))
               (<= (+ (col ?b) (row ?b)) (+ (band ?t) 25))
               (<= (- (row ?b) (col ?b)) (+ (band ?t) 25))
          )
          :effect (and(rescued ?t))
     )

)
