(define (problem kitchen-line-p05)
(:domain kitchen-line)
(:objects
	chef0 - chef
	utensil0 - utensil
	utensil1 - utensil
	utensil2 - utensil
	chef1 - chef
	utensil3 - utensil
	utensil4 - utensil
	utensil5 - utensil
	chef2 - chef
	utensil6 - utensil
	utensil7 - utensil
	utensil8 - utensil
	plating1 - garnish
	griddle0 - garnish
	entree2 - recipe
	pantry0 - recipe
	entree1 - recipe
	dessert3 - recipe
	dessert4 - recipe
	dessert5 - recipe
	appetiser6 - recipe
)
(:init
	(prepares utensil0 plating1)
	(prepares utensil0 griddle0)
	(sharpening_recipe utensil0 entree1)
	(prepares utensil1 griddle0)
	(prepares utensil1 plating1)
	(sharpening_recipe utensil1 entree2)
	(prepares utensil2 griddle0)
	(prepares utensil2 plating1)
	(sharpening_recipe utensil2 entree1)
	(carries utensil0 chef0)
	(carries utensil1 chef0)
	(carries utensil2 chef0)
	(energy_spare chef0)
	(focused_on chef0 entree1)
	(prepares utensil3 plating1)
	(prepares utensil3 griddle0)
	(sharpening_recipe utensil3 entree2)
	(prepares utensil4 plating1)
	(sharpening_recipe utensil4 entree1)
	(prepares utensil5 griddle0)
	(sharpening_recipe utensil5 entree2)
	(carries utensil3 chef1)
	(carries utensil4 chef1)
	(carries utensil5 chef1)
	(energy_spare chef1)
	(focused_on chef1 entree1)
	(prepares utensil6 plating1)
	(prepares utensil6 griddle0)
	(sharpening_recipe utensil6 pantry0)
	(prepares utensil7 griddle0)
	(prepares utensil7 plating1)
	(sharpening_recipe utensil7 entree1)
	(prepares utensil8 griddle0)
	(sharpening_recipe utensil8 entree1)
	(carries utensil6 chef2)
	(carries utensil7 chef2)
	(carries utensil8 chef2)
	(energy_spare chef2)
	(focused_on chef2 dessert3)
)
(:goal (and
	(have_dish dessert3 griddle0)
	(have_dish dessert4 griddle0)
	(have_dish dessert5 griddle0)
	(have_dish appetiser6 griddle0)
))

)
