(define (domain kitchen-line)
  (:requirements :strips :typing)
  (:types chef recipe utensil garnish)
  (:predicates
  (carries ?i - utensil ?s - chef)
  (prepares ?i - utensil ?m - garnish)
  (focused_on ?s - chef ?d - recipe)
  (energy_spare ?s - chef)
  (energy_active ?i - utensil)
  (sharpened ?i - utensil)
  (have_dish ?d - recipe ?m - garnish)
  (sharpening_recipe ?i - utensil ?d - recipe))

  (:action switch_focus
   :parameters (?s - chef ?d_new - recipe ?d_prev - recipe)
   :precondition (and (focused_on ?s ?d_prev))
   :effect (and  (focused_on ?s ?d_new)
                 (not (focused_on ?s ?d_prev))))

  (:action fire_up
   :parameters (?i - utensil ?s - chef)
   :precondition (and (carries ?i ?s)
                      (energy_spare ?s))
   :effect (and (energy_active ?i)
                (not (sharpened ?i))
                (not (energy_spare ?s))))

  (:action cool_down
   :parameters (?i - utensil ?s - chef)
   :precondition (and (carries ?i ?s)
                      (energy_active ?i))
   :effect (and (not (energy_active ?i))
                (energy_spare ?s)))

  (:action sharpen
   :parameters (?s - chef ?i - utensil ?d - recipe)
   :precondition (and (carries ?i ?s)
          (sharpening_recipe ?i ?d)
                      (focused_on ?s ?d)
                      (energy_active ?i))
   :effect (sharpened ?i))

  (:action plate_dish
   :parameters (?s - chef ?d - recipe ?i - utensil ?m - garnish)
   :precondition (and (sharpened ?i)
                      (carries ?i ?s)
                      (prepares ?i ?m)
                      (energy_active ?i)
                      (focused_on ?s ?d))
   :effect (have_dish ?d ?m)
