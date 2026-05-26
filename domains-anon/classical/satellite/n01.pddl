(define (problem strips_sat_x_1)
(:domain kitchen-line)
(:objects
  chef0 - chef
  utensil0 - utensil
  chef1 - chef
  utensil1 - utensil
  chef2 - chef
  utensil2 - utensil
  broiler0 - garnish
  pantry0 - recipe
  dessert1 - recipe
)
(:init
  (prepares utensil0 broiler0)
  (sharpening_recipe utensil0 pantry0)
  (carries utensil0 chef0)
  (energy_spare chef0)
  (focused_on chef0 dessert1)
  (prepares utensil1 broiler0)
  (sharpening_recipe utensil1 pantry0)
  (carries utensil1 chef1)
  (energy_spare chef1)
  (focused_on chef1 dessert1)
  (prepares utensil2 broiler0)
  (sharpening_recipe utensil2 pantry0)
  (carries utensil2 chef2)
  (energy_spare chef2)
  (focused_on chef2 pantry0)
  (carries utensil9 chef0)
)
(:goal (and
  (focused_on chef1 pantry0)
  (focused_on chef2 pantry0)
  (have_dish dessert1 broiler0)
))

)
