# select accuweather sensors
python3 -m tools.sensor_select \
    --grid-width 112 \
    --grid-height 56 \
    --sensors-per-cell 1 \
    --exclude-countries IRN IRQ KWT CUB VEN TUN MAR SAU KGZ TJK BRA ARG DMA URY CHL PRY CHN KAZ AFG PAK RUS COL GUY SUR BRB PAN GTM IND PER BOL LKA MUS REU ANT LCA MTQ GLP VIR PRI HTI JAM CYM CRI NIC HND NZL FJI VUT NCL BGD NPL MMR ISL \
    --mask-snapshot .dev/sensor_selection/1724773800.zip \
    --output .dev/sensor_selection/aw_sensors.csv

# select weatherkit sensors
python3 -m tools.sensor_select \
    --include-countries USA GBR \
    --grid-width 280 \
    --grid-height 140 \
    --sensors-per-cell 1 \
    --mask-snapshot .dev/sensor_selection/1724773800.zip \
    --output .dev/sensor_selection/wk_sensors.csv
