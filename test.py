import os
import re

import snappy
from snappy import ProductIO, WKTReader
import geomet.wkt
import geojson

def geojson_to_wkt(geojson_obj, feature_number=0, decimals=4):
    """Convert a GeoJSON object to Well-Known Text. Intended for use with OpenSearch queries.

    In case of FeatureCollection, only one of the features is used (the first by default).
    3D points are converted to 2D.

    Parameters
    ----------
    geojson_obj : dict
        a GeoJSON object
    feature_number : int, optional
        Feature to extract polygon from (in case of MultiPolygon
        FeatureCollection), defaults to first feature
    decimals : int, optional
        Number of decimal figures after point to round coordinate to. Defaults to 4 (about 10
        meters).

    Returns
    -------
    str
        Well-Known Text string representation of the geometry
    """
    if "coordinates" in geojson_obj:
        geometry = geojson_obj
    elif "geometry" in geojson_obj:
        geometry = geojson_obj["geometry"]
    else:
        geometry = geojson_obj["features"][feature_number]["geometry"]

    def ensure_2d(geometry):
        if isinstance(geometry[0], (list, tuple)):
            return list(map(ensure_2d, geometry))
        else:
            return geometry[:2]

    def check_bounds(geometry):
        if isinstance(geometry[0], (list, tuple)):
            return list(map(check_bounds, geometry))
        else:
            if geometry[0] > 180 or geometry[0] < -180:
                raise ValueError("Longitude is out of bounds, check your JSON format or data")
            if geometry[1] > 90 or geometry[1] < -90:
                raise ValueError("Latitude is out of bounds, check your JSON format or data")

    # Discard z-coordinate, if it exists
    geometry["coordinates"] = ensure_2d(geometry["coordinates"])
    check_bounds(geometry["coordinates"])

    wkt = geomet.wkt.dumps(geometry, decimals=decimals)
    # Strip unnecessary spaces
    wkt = re.sub(r"(?<!\d) ", "", wkt)
    return wkt


# Sentinel2 - Level 1
for file in os.listdir('/app/input/Sentinel2/Level1/'):
    print(file)
    product = ProductIO.readProduct('/app/input/Sentinel2/Level1/' + file)

    # Resampling
    HashMap = snappy.jpy.get_type('java.util.HashMap')
    parameters = HashMap()
    parameters.put('targetResolution', 10)
    resample_product = snappy.GPF.createProduct('Resample', parameters, product)

    # Subset
    with open ('/app/aoi.geojson') as f:
        aoi = geojson_to_wkt(geojson.load(f))

    geom = WKTReader().read(aoi)

    SubsetOp = snappy.jpy.get_type('org.esa.snap.core.gpf.common.SubsetOp')
    parameters = HashMap()
    parameters.put('geoRegion', geom)
    parameters.put('copyMetadata', "true")
    sub_product = snappy.GPF.createProduct('Subset', parameters, resample_product)

    # Atmospheric correction - c2rcc
    parameters = HashMap()
    # C2RCC-Nets, C2X-Nets, C2X-COMPLEX-Nets
    parameters.put('PnetSet', 'C2RCC-Nets')
    parameters.put('elevation', 0.0)
    parameters.put('salinity', 38.4)
    parameters.put('temperature', 18.0)
    parameters.put('ozone', 334.68)
    parameters.put('press', 1014.837)
    parameters.put('outputAsRrs', False)
    parameters.put('deriveRwFromPathAndTransmittance', False)
    parameters.put('outputRtoa', False)
    parameters.put('outputRtosaGc', False)
    parameters.put('outputRtosaGcAann', False)
    parameters.put('outputRpath', False)
    parameters.put('outputTdown', False)
    parameters.put('outputTup', False)
    parameters.put('outputAcReflectance', False)
    parameters.put('outputRhown', True)
    parameters.put('outputOos', False)
    parameters.put('outputKd', True)
    parameters.put('outputUncertainties', True)

    atmcor_product = snappy.GPF.createProduct('c2rcc.msi', parameters, sub_product)


    # Get water quality values

    # Point-based

    # Average

    # Write output (unnecessary)

    ac_date = file.split('_')[2]
    nameStart = 'Atm_cor_Subset_Resampled_S2_MSIL1C_'
    nameEnd = '.dim'

    ProductIO.writeProduct(sub_product, '/app/output/Sentinel2/Level1/' + nameStart \
                            + ac_date + nameEnd, "BEAM-DIMAP")

    print("Done")
