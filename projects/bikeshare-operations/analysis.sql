-- Denominator is the number of *observed* hours in each group. Missing hours are
-- reported separately; zeros are never imputed for absent observations.
-- QUERY: hourly_profiles
SELECT working_day, hour, COUNT(*) AS observed_hours,
       ROUND(AVG(rentals), 2) AS mean_rentals,
       ROUND(AVG(registered), 2) AS mean_registered,
       ROUND(AVG(casual), 2) AS mean_casual
FROM hourly
GROUP BY working_day, hour
ORDER BY working_day, hour;
-- QUERY: peak_hours
WITH profiles AS (
  SELECT working_day, hour, COUNT(*) AS observed_hours,
         ROUND(AVG(rentals), 2) AS mean_rentals
  FROM hourly GROUP BY working_day, hour
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY working_day ORDER BY mean_rentals DESC, hour ASC
  ) AS demand_rank FROM profiles
)
SELECT working_day, hour, observed_hours, mean_rentals
FROM ranked WHERE demand_rank <= 3
ORDER BY working_day, demand_rank;
