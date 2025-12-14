Your task is to write a simple API and database schema for a steel plant's production plans.

Depending on the kind of plan the customer wants to produce, steel production is specified either in terms of

1. A sequence of heats (batches of steel) of specified steel grades to be made each day
2. A coarse breakdown into different product groups. Each steel grade belongs to a specific
product group, but each product group comprises many steel grades.

However, ScrapChef requires a steel grade breakdown (number of heats of each grade) in order to run.

We have provided some example input files, as well as the number of tons of each steel grade
made in the last few months (you can assume each heat averages 100t of steel produced).

The API should:

1. Accept these files and store them in your database schema (you may change them to a more friendly
format before uploading)

2. Create an endpoint to forecast the September production in a format that ScrapChef can use. For this
part of the task, there is no single correct answer. You should think about what the customer might
reasonably want to produce based on the product group breakdown and the historical production.

Where relevant, briefly document the business logic and the assumptions you are making.

Feel free to ask any clarifying questions at any point.