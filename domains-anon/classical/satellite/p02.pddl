(define (problem kitchen-line-p02)
(:domain kitchen-line)
(:objects
	chef0 - chef
	utensil0 - utensil
	utensil1 - utensil
	chef1 - chef
	utensil2 - utensil
	griddle0 - garnish
	pantry1 - recipe
	entree0 - recipe
	appetiser2 - recipe
	entree3 - recipe
)
(:init
	(prepares utensil0 griddle0)
	(sharpening_recipe utensil0 pantry1)
	(prepares utensil1 griddle0)
	(sharpening_recipe utensil1 pantry1)
	(carries utensil0 chef0)
	(carries utensil1 chef0)
	(energy_spare chef0)
	(focused_on chef0 entree0)
	(prepares utensil2 griddle0)
	(sharpening_recipe utensil2 entree0)
	(carries utensil2 chef1)
	(energy_spare chef1)
	(focused_on chef1 pantry1)
)
(:goal (and
	(focused_on chef0 pantry1)
	(have_dish appetiser2 griddle0)
	(have_dish entree3 griddle0)
))

)
