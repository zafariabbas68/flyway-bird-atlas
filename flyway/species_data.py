"""Species definitions for the Flyway migration model.

IMPORTANT - these are *modelled, illustrative* ranges and routes, written from
general knowledge of each species. They are NOT eBird Status & Trends data and
NOT real GPS tracks. See docs/ANALYSIS.md for how to plug real data in.

Coordinates are (lon, lat) in degrees. Range components are Gaussians:
    (lon, lat, sigma_lon, sigma_lat, weight)

Timing is in weeks of the year (0 = first week of January), as
    (mean_departure_week, sd_departure_weeks, mean_duration_weeks, sd_duration_weeks)

Route waypoints are listed in the direction of travel. Spring routes run
winter -> breeding, fall routes run breeding -> winter. If `route_fall` is
missing, the spring waypoints are reused in reverse.
"""
from __future__ import annotations

SPECIES: list[dict] = [
    # ------------------------------------------------------------------ 1
    {
        "id": "wood-thrush",
        "common": "Wood Thrush",
        "latin": "Hylocichla mustelina",
        "group": "Eastern neotropical migrant",
        "color": "#ffb020",
        "strategy": "Night flier",
        "tagline": "A forest songbird that crosses the Gulf of Mexico in the dark.",
        "view": {"center": [-86, 24], "span": 40},
        "breeding": [(-82, 37, 5.0, 4.0, 0.50), (-76, 41, 3.0, 3.0, 0.30), (-90, 34, 4.0, 3.0, 0.20)],
        "winter": [(-89, 17.5, 3.0, 2.0, 0.35), (-86, 14, 3.0, 2.0, 0.35), (-84, 10, 2.5, 1.5, 0.30)],
        "route_spring": [(-87.5, 20.5), (-89.5, 25.5), (-90, 30)],
        "spring": (14, 2.0, 4.5, 0.8),
        "fall": (34, 3.5, 6.0, 1.0),
        "pause": 0.35,
        "corridor": 1.6,
        "steps": [
            {
                "week": None,
                "title": "A year in motion",
                "body": "Each glowing patch is where Wood Thrushes are most likely to be found that week. Watch the whole population drain out of the eastern forests in autumn and flow back every spring.",
                "labels": [],
            },
            {
                "week": 3,
                "title": "Winter in the lowland forest",
                "body": "In January nearly every Wood Thrush is in the humid forests between southern Mexico and Panama, packed into a thin ribbon of habitat far smaller than their summer range.",
                "labels": [
                    {"text": "Yucatan lowlands", "lon": -88.5, "lat": 18.5, "dx": -150, "dy": -70},
                    {"text": "Costa Rica and Panama", "lon": -84, "lat": 9.5, "dx": -190, "dy": 70},
                ],
            },
            {
                "week": 16,
                "title": "One night over open water",
                "body": "Small songbirds leave at dusk and fly through the night. Many take the direct route over the Gulf of Mexico, roughly a thousand kilometres with nowhere to land.",
                "labels": [
                    {"text": "Gulf of Mexico crossing", "lon": -90, "lat": 25, "dx": 120, "dy": 80},
                    {"text": "First forest after the water", "lon": -90, "lat": 30.2, "dx": -170, "dy": -50},
                ],
            },
            {
                "week": 26,
                "title": "Summer across the east",
                "body": "By June the birds have spread out over the deciduous forests of the eastern United States. The same number of birds now covers many times the area, so the glow turns faint.",
                "labels": [
                    {"text": "Appalachian forests", "lon": -81, "lat": 37, "dx": 140, "dy": -40},
                    {"text": "Great Lakes", "lon": -83, "lat": 44, "dx": -150, "dy": -40},
                ],
            },
            {
                "week": 40,
                "title": "The long way back",
                "body": "Young and old birds head south again from late summer. The dispersal of departure dates is wide, so the southward pulse arrives as a slow wave rather than a single rush.",
                "labels": [
                    {"text": "Return crossing", "lon": -90, "lat": 25, "dx": 110, "dy": 80},
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 2
    {
        "id": "western-tanager",
        "common": "Western Tanager",
        "latin": "Piranga ludoviciana",
        "group": "Western neotropical migrant",
        "color": "#ff5a5f",
        "strategy": "Mountain route",
        "tagline": "Breeds farther north than any other tanager and winters in the Mexican highlands.",
        "view": {"center": [-108, 30], "span": 38},
        "breeding": [(-118, 45, 6.0, 4.0, 0.50), (-112, 51, 5.0, 4.0, 0.25), (-108, 41, 4.0, 3.0, 0.25)],
        "winter": [(-104, 20, 4.0, 2.5, 0.50), (-95, 16, 3.0, 2.0, 0.25), (-88, 13.5, 2.5, 1.5, 0.25)],
        "route_spring": [(-103, 24.5), (-108, 30.5), (-111, 36)],
        "spring": (14, 2.0, 5.0, 0.9),
        "fall": (31, 3.0, 7.0, 1.2),
        "pause": 0.40,
        "corridor": 2.0,
        "steps": [
            {
                "week": None,
                "title": "West of the Rockies",
                "body": "Western birds follow a different map. They breed from the mountains to the Pacific coast, and they migrate through dry country where stopover habitat is patchy.",
                "labels": [],
            },
            {
                "week": 2,
                "title": "Winter in Mexico and beyond",
                "body": "Most of the population spends the winter in Mexico's pine-oak highlands and along the Pacific slope, with a thinner stream reaching Central America.",
                "labels": [
                    {"text": "Sierra Madre highlands", "lon": -104, "lat": 21, "dx": -150, "dy": -60},
                    {"text": "Pacific slope of Central America", "lon": -90, "lat": 14, "dx": 70, "dy": 80},
                ],
            },
            {
                "week": 17,
                "title": "Following the spring green-up",
                "body": "Tanagers move north as insects emerge and fruit ripens. They arrive in the southwestern deserts in waves, stopping wherever a tree line or river corridor offers cover.",
                "labels": [
                    {"text": "Desert river corridors", "lon": -109, "lat": 31.5, "dx": 100, "dy": 70},
                ],
            },
            {
                "week": 27,
                "title": "The farthest north of any tanager",
                "body": "Summer finds the species from northern California into western Canada. Some birds nest well into the boreal forest, a long way from where the species began its journey.",
                "labels": [
                    {"text": "Pacific Northwest", "lon": -121, "lat": 46, "dx": -170, "dy": -10},
                    {"text": "Canadian Rockies", "lon": -114, "lat": 52, "dx": 120, "dy": -50},
                ],
            },
            {
                "week": 36,
                "title": "A slow, early start south",
                "body": "Fall departures begin in July for some birds, and the trip stretches over two months. The slow drift keeps the glow moving for much of the second half of the year.",
                "labels": [],
            },
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "id": "white-throated-sparrow",
        "common": "White-throated Sparrow",
        "latin": "Zonotrichia albicollis",
        "group": "Short-distance migrant",
        "color": "#35e0ff",
        "strategy": "Short hop",
        "tagline": "Winters in the southeastern United States and breeds in the northern forests of Canada.",
        "view": {"center": [-92, 44], "span": 27},
        "breeding": [(-95, 54, 12.0, 4.0, 0.40), (-75, 50, 8.0, 3.0, 0.35), (-110, 56, 5.0, 3.0, 0.25)],
        "winter": [(-84, 33, 6.0, 3.0, 0.50), (-95, 31, 5.0, 2.5, 0.25), (-75, 37, 3.0, 3.0, 0.25)],
        "route_spring": [(-88, 40), (-90, 46)],
        "spring": (11, 2.5, 6.5, 1.2),
        "fall": (38, 2.5, 6.0, 1.2),
        "pause": 0.55,
        "corridor": 3.0,
        "steps": [
            {
                "week": None,
                "title": "Migration without the tropics",
                "body": "Not every migrant needs a passport. Birds like this sparrow shift a few thousand kilometres within the temperate zone, tracking snow lines and food rather than the equator.",
                "labels": [],
            },
            {
                "week": 3,
                "title": "A southern winter",
                "body": "In midwinter the sparrows spread across the southeastern states and the Gulf coast, sharing backyards and brushy edges with local birds.",
                "labels": [
                    {"text": "Southeastern United States", "lon": -84, "lat": 33, "dx": 120, "dy": 60},
                ],
            },
            {
                "week": 18,
                "title": "A leisurely spring",
                "body": "Compared with the thrush, the sparrow's departure is spread across many weeks. Short legs and frequent stops mean the northward front moves slowly and smears out.",
                "labels": [
                    {"text": "Slow northward front", "lon": -90, "lat": 41, "dx": -170, "dy": -30},
                ],
            },
            {
                "week": 27,
                "title": "Boreal summer",
                "body": "By early summer the species occupies a belt of spruce and mixed forest from the Rockies to the Atlantic. The song is a thin whistle that carries a long way through the trees.",
                "labels": [
                    {"text": "Boreal forest belt", "lon": -92, "lat": 54, "dx": 130, "dy": -60},
                ],
            },
            {
                "week": 43,
                "title": "Ahead of the snow",
                "body": "Fall movement tracks the cold. Birds leave when the first hard frosts arrive and settle once they have found enough seed and shelter.",
                "labels": [],
            },
        ],
    },
    # ------------------------------------------------------------------ 4
    {
        "id": "broad-winged-hawk",
        "common": "Broad-winged Hawk",
        "latin": "Buteo platypterus",
        "group": "Soaring migrant",
        "color": "#ff4fd8",
        "strategy": "Rides thermals",
        "tagline": "Gathers in swirling flocks and funnels through Central America every autumn.",
        "view": {"center": [-80, 20], "span": 40},
        "breeding": [(-82, 43, 8.0, 5.0, 0.50), (-90, 47, 5.0, 3.0, 0.20), (-70, 45, 4.0, 3.0, 0.30)],
        "winter": [(-72, 5, 5.0, 3.0, 0.40), (-76, -4, 3.0, 3.0, 0.30), (-65, 6, 4.0, 3.0, 0.30)],
        "route_spring": [(-76, 7.5), (-82, 9.5), (-87, 13.5), (-93, 17.5), (-96.5, 21), (-97.5, 27.5), (-96, 35)],
        "spring": (12, 1.2, 5.0, 0.6),
        "fall": (37, 1.2, 6.0, 0.7),
        "pause": 0.08,
        "corridor": 1.0,
        "steps": [
            {
                "week": None,
                "title": "Birds that refuse to flap",
                "body": "Hawks cannot afford to flap for thousands of kilometres. They climb in columns of warm rising air, glide down the coast of the continent, then climb again.",
                "labels": [],
            },
            {
                "week": 4,
                "title": "Winter in northern South America",
                "body": "The wintering population is concentrated in forests across Colombia, Venezuela and the upper Amazon, far from the trees where they nested.",
                "labels": [
                    {"text": "Colombia and Venezuela", "lon": -70, "lat": 6, "dx": 110, "dy": -60},
                    {"text": "Upper Amazon", "lon": -75, "lat": -4, "dx": -130, "dy": 40},
                ],
            },
            {
                "week": 14,
                "title": "A funnel with land on both sides",
                "body": "Thermals only form over land, so the hawks avoid long water crossings. Their route squeezes into a thin corridor through Panama and Central America, making the stream very dense and very narrow.",
                "labels": [
                    {"text": "Central American funnel", "lon": -86.5, "lat": 13, "dx": -170, "dy": -40},
                    {"text": "Gulf coast bottleneck", "lon": -96.5, "lat": 22, "dx": -80, "dy": -100},
                ],
            },
            {
                "week": 26,
                "title": "Back in the northern forest",
                "body": "By summer the population has dispersed over eastern woodlands, and the corridor that carried thousands of birds a day is empty.",
                "labels": [
                    {"text": "Eastern woodlands", "lon": -80, "lat": 44, "dx": 130, "dy": -40},
                ],
            },
            {
                "week": 40,
                "title": "A tight autumn pulse",
                "body": "Fall departures are much more synchronised than most species. In a few weeks the whole population drains from the north, with big flocks forming over the same ridges year after year.",
                "labels": [
                    {"text": "Fall funnel", "lon": -88, "lat": 15, "dx": -170, "dy": -60},
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "id": "eastern-kingbird",
        "common": "Eastern Kingbird",
        "latin": "Tyrannus tyrannus",
        "group": "Long-distance migrant",
        "color": "#a6ff3d",
        "strategy": "Day flocks",
        "tagline": "Crosses an entire hemisphere to spend the northern winter in the western Amazon.",
        "view": {"center": [-85, 18], "span": 50},
        "breeding": [(-100, 46, 9.0, 5.0, 0.50), (-80, 42, 6.0, 4.0, 0.30), (-115, 52, 4.0, 3.0, 0.20)],
        "winter": [(-70, -8, 4.0, 4.0, 0.50), (-64, -14, 3.0, 3.0, 0.30), (-76, -2, 2.5, 2.5, 0.20)],
        "route_spring": [(-75, 0.5), (-77, 7), (-83.5, 10), (-90, 16), (-94, 22), (-96.5, 29)],
        "spring": (14, 2.0, 7.0, 1.0),
        "fall": (33, 2.0, 7.0, 1.0),
        "pause": 0.30,
        "corridor": 2.0,
        "steps": [
            {
                "week": None,
                "title": "The longest commute",
                "body": "A bird that nests in a Minnesota hedgerow may spend its winter near the foothills of the Andes. This is migration at hemispheric scale.",
                "labels": [],
            },
            {
                "week": 3,
                "title": "A winter in the canopy",
                "body": "During the northern winter these flycatchers live in western Amazonia and feed heavily on fruit, a very different diet from the insects they chase in summer.",
                "labels": [
                    {"text": "Western Amazon basin", "lon": -70, "lat": -8, "dx": 130, "dy": -50},
                ],
            },
            {
                "week": 18,
                "title": "Northward through Central America",
                "body": "The spring route threads the land bridge. Birds travel by day in loose groups, building to a broad band across Mexico and the Gulf coast.",
                "labels": [
                    {"text": "Land bridge", "lon": -83.5, "lat": 10, "dx": -150, "dy": 60},
                    {"text": "Gulf coast", "lon": -94, "lat": 22, "dx": -110, "dy": -60},
                ],
            },
            {
                "week": 26,
                "title": "A continent-wide summer",
                "body": "Kingbirds breed over most of temperate North America east of the Rockies. They defend territories noisily against crows and hawks much larger than themselves.",
                "labels": [
                    {"text": "Great Plains", "lon": -100, "lat": 46, "dx": -130, "dy": -60},
                    {"text": "Eastern lakes", "lon": -80, "lat": 43, "dx": 140, "dy": -30},
                ],
            },
            {
                "week": 36,
                "title": "A head start in August",
                "body": "Fall departures begin before many other songbirds have started. By September the northern range is empty.",
                "labels": [],
            },
        ],
    },
    # ------------------------------------------------------------------ 6
    {
        "id": "blackpoll-warbler",
        "common": "Blackpoll Warbler",
        "latin": "Setophaga striata",
        "group": "Over-water migrant",
        "color": "#a07bff",
        "strategy": "Open-ocean flight",
        "tagline": "A twelve-gram songbird that leaves New England and flies out over the Atlantic.",
        "view": {"center": [-100, 24], "span": 60},
        "breeding": [(-150, 63, 6.0, 3.0, 0.20), (-120, 60, 10.0, 4.0, 0.35), (-100, 57, 6.0, 3.0, 0.10), (-70, 50, 8.0, 4.0, 0.35)],
        "winter": [(-65, -5, 6.0, 4.0, 0.50), (-72, -12, 3.0, 3.0, 0.25), (-62, 5, 4.0, 3.0, 0.25)],
        "route_spring": [(-62, 5.5), (-66, 14), (-76, 22), (-80.5, 29), (-79.5, 36)],
        "route_fall": [(-70, 45), (-64, 38), (-62, 30), (-64, 21), (-63, 12)],
        "spring": (11, 2.0, 9.0, 1.3),
        "fall": (35, 2.0, 7.5, 1.2),
        "pause": 0.25,
        "corridor": 1.8,
        "steps": [
            {
                "week": None,
                "title": "Two different routes",
                "body": "This species flies a loop. In spring it hugs islands and the coast. In fall it takes a startling shortcut over the open Atlantic.",
                "labels": [],
            },
            {
                "week": 4,
                "title": "Winter in Amazonia",
                "body": "While North America sits under snow, the whole population is south of the equator, spread across the Amazon basin and the Guianas.",
                "labels": [
                    {"text": "Amazon basin", "lon": -64, "lat": -5, "dx": 120, "dy": 20},
                ],
            },
            {
                "week": 18,
                "title": "A slow trip north",
                "body": "The spring leg lasts more than two months. Birds follow the Caribbean arc and the Florida peninsula, then spread west across boreal Canada all the way to Alaska.",
                "labels": [
                    {"text": "Caribbean arc", "lon": -72, "lat": 18, "dx": 100, "dy": 60},
                    {"text": "Florida", "lon": -80.5, "lat": 28, "dx": -140, "dy": 50},
                ],
            },
            {
                "week": 26,
                "title": "The broadest breeding range",
                "body": "From Alaska to Newfoundland, blackpolls nest in the spruce forest along the northern edge of the tree line.",
                "labels": [
                    {"text": "Alaska", "lon": -150, "lat": 63, "dx": 70, "dy": -60},
                    {"text": "Maritime Canada", "lon": -66, "lat": 47, "dx": 100, "dy": -60},
                ],
            },
            {
                "week": 40,
                "title": "Three days, no landing",
                "body": "In autumn the warblers fatten up, then leave the northeast coast and fly out over the Atlantic. The nonstop flight to the Caribbean or South America can take around three days.",
                "labels": [
                    {"text": "Open Atlantic", "lon": -62, "lat": 30, "dx": 90, "dy": -50},
                ],
            },
        ],
    },
    # ------------------------------------------------------------------ 7
    {
        "id": "rufous-hummingbird",
        "common": "Rufous Hummingbird",
        "latin": "Selasphorus rufus",
        "group": "Loop migrant",
        "color": "#2dffb2",
        "strategy": "Seasonal loop",
        "tagline": "A three-gram bird that goes north along the coast and returns south through the mountains.",
        "view": {"center": [-112, 34], "span": 34},
        "breeding": [(-122, 46, 3.0, 3.0, 0.40), (-125, 52, 3.0, 3.0, 0.30), (-133, 58, 4.0, 3.0, 0.15), (-116, 48, 3.0, 2.0, 0.15)],
        "winter": [(-100, 19, 4.0, 2.5, 0.60), (-97, 22, 3.0, 2.0, 0.20), (-92, 17, 3.0, 2.0, 0.20)],
        "route_spring": [(-105, 22.5), (-112, 29.5), (-117.5, 34.5), (-122, 40)],
        "route_fall": [(-117, 47), (-111, 42), (-108, 36), (-105, 29), (-102, 23.5)],
        "spring": (7, 2.0, 9.0, 1.2),
        "fall": (26, 2.5, 11.0, 1.5),
        "pause": 0.45,
        "corridor": 1.2,
        "steps": [
            {
                "week": None,
                "title": "A loop, not a line",
                "body": "The outbound and return routes are not the same. Watch the glow climb the Pacific edge in spring and fall back down through the interior in summer.",
                "labels": [],
            },
            {
                "week": 2,
                "title": "Winter in Mexico",
                "body": "Rufous Hummingbirds winter in the pine-oak forests of central and southern Mexico, where flowering shrubs offer nectar through the dry season.",
                "labels": [
                    {"text": "Central Mexico highlands", "lon": -100, "lat": 19.5, "dx": 100, "dy": -60},
                ],
            },
            {
                "week": 14,
                "title": "Following the coast",
                "body": "Spring migration starts early, as soon as the first flowers open. The birds take the Pacific side of the continent, where blooms appear in a steady northward sequence.",
                "labels": [
                    {"text": "Pacific flyway", "lon": -117.5, "lat": 34.5, "dx": -110, "dy": 70},
                ],
            },
            {
                "week": 24,
                "title": "The northernmost nesters",
                "body": "Some females nest as far north as southeast Alaska, the most northern breeding of any hummingbird. The model puts most birds in the Pacific Northwest.",
                "labels": [
                    {"text": "Pacific Northwest", "lon": -123, "lat": 47, "dx": -140, "dy": -50},
                    {"text": "Alaska panhandle", "lon": -133, "lat": 57, "dx": -90, "dy": -30},
                ],
            },
            {
                "week": 34,
                "title": "Back through the mountains",
                "body": "By midsummer the birds are already heading south, this time through the Rockies, where late-summer wildflowers are in bloom at high elevation.",
                "labels": [
                    {"text": "Rocky Mountain meadows", "lon": -110, "lat": 41, "dx": 120, "dy": -30},
                ],
            },
        ],
    },
]


def get_species(species_id: str) -> dict | None:
    for sp in SPECIES:
        if sp["id"] == species_id:
            return sp
    return None
