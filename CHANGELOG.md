# Changelog

## `0.3.1`
- Handle Vaisala API rate limit response
- Add Rainbow precip-global layer

## `0.3.0`
- Implement evaluator - function to implement flexible approach for event metric calculation
- Fix warnings in test
- Always store metrics result in session metrics folder

## `0.2.7`
- Allow collection of parsing jobs instead of immediately running them

## `0.2.6`
- Refactor extracting of precipitation values from tile provider
- Refactor WeatherKit forecast downloader to support multiple forecast types

## `0.2.5`
- Allow collection of calculation jobs instead of immediately running them 

## `0.2.4`
- Optimize checkout job batching and s3 client utilization

## `0.2.3`
- Add meteo agencies measurement stations (CHE - FSDI, AUT - GeoSphere, GER - DWD)

## `0.2.2`
- Add fetching reports to the forecast downloading tool
- Add support for different download implementations in CheckoutExecutor 

## `0.2.1`
- Use asynchronous forecast data downloading
- Fix requirements.dev.txt paths
- Fix parser mapping for convenient inheritance and enhancements
- Make checkout inheritable by refactoring function into executor class
- Fix parser/manager mapping to data vendor enum value

## `0.2.0`

- Ready for opensource
