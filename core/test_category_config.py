"""
test_category_config.py - Test Category Configuration Definitions

Central configuration file defining all test categories and their error metrics
for both CUSLT and ADF printer quality testing.
"""

class TestCategoryConfig:
    """
    Configuration for a single test category.
    """
    
    def __init__(self, name, error_column_config, threshold_specs, total_column_name, additional_groupby_cols=None):

        self.name = name
        self.error_column_config = error_column_config
        self.threshold_specs = threshold_specs
        self.total_column_name = total_column_name
        self.additional_groupby_cols = additional_groupby_cols or []

        self._uses_print_mode = self.check_print_mode_usage()
    
    def check_print_mode_usage(self):
        """
        Check if any threshold specification uses print mode.
        """
        for value in self.threshold_specs.values():
            if isinstance(value, dict):
                return True
        return False

    def get_spec_for_media_type(self, media_type, print_mode=None):
        """
        Get the Pass/Fail threshold for a specific media type and print mode.
        """
        # Get the spec for this media type (default to 5 if not found)
        spec = self.threshold_specs.get(media_type, 5)
        
        # If spec is a dict, we need print mode
        if isinstance(spec, dict):
            if print_mode is None:
                # If no print mode provided, return a default
                return 5
            # Return the threshold for this specific print mode
            return spec.get(print_mode, 5)
        else:
            # Simple number threshold
            return spec


# ============================================================================
# CUSLT CATEGORY DEFINITIONS
# ============================================================================

INTERVENTION_CONFIG = TestCategoryConfig(
    name="Intervention",
    error_column_config={
        'NP': ['NP_Top', 'NP_Middle', 'NP_Bottom1', 'NP_Bottom2', 'NP_Last Page'],
        'MP': ['MP_Top', 'MP_Middle', 'MP_Bottom1', 'MP_Bottom2', 'MP_Last page', 'MMP_Top', 'MMP_Middle', 'MMP_Bottom1', 'MMP_Bottom2', 'MMP_Last page'],
        'TP': ['TP_Top', 'TP_Middle', 'TP_Bottom1', 'TP_Bottom2', 'TP_Last page'],
        'PJ': ['PJ_S1_Z1', 'PJ_S1_Z2', 'PJ_S1_Z3', 'PJ_S1_Z4', 'PJ_S1_Z5', 'PJ_S1_Z6', 'PJ_S1_Z7', 'PJ_S1_Z8', 'PJ_S2_Z1', 'PJ_S2_Z2', 'PJ_S2_Z3', 'PJ_S2_Z4', 'PJ_S2_Z5',
               'PJ_S2_Z6', 'PJ_S2_Z7', 'PJ_S2_Z8'],
        'PS': ['PS_S1_Z1', 'PS_S1_Z2', 'PS_S1_Z3', 'PS_S1_Z4', 'PS_S1_Z5', 'PS_S1_Z6', 'PS_S1_Z7', 'PS_S1_Z8', 'PS_S2_Z1', 'PS_S2_Z2', 'PS_S2_Z3', 'PS_S2_Z4', 
               'PS_S2_Z5', 'PS_S2_Z6', 'PS_S2_Z7', 'PS_S2_Z8']
    },
    threshold_specs={
        'Plain': 0.58,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 10
    },
    total_column_name="Sum of Total Intervention"
)

SOFT_ERROR_CONFIG = TestCategoryConfig(
    name="Soft Error",
    error_column_config={
        'Messy Output': 'Messy Output',
        'Fallen Sheet': 'Fallen Sheet',
        'Paper Sailing': 'Paper Sailing',
        'Paper Stuck in Funnel': 'Paper Stuck in Funnel',
        'Bull Dozing': 'Bull Dozing',
        'Paper Disorder': 'Paper Disorder',
        'Paper Suck Back': 'Paper Suck Back',
        'Paper not Fully Eject': 'Paper not Fully Eject',
        'Paper Curl': 'Paper Curl',
        'Paper Rolled Up': 'Paper Rolled Up',
        'False Output Tray Full': 'False Output Tray Full',
        'Tear_S1': 'Tear_S1',
        'Tear_S2': 'Tear_S2',
        'Dent_S1': 'Dent_S1',
        'Dent_S2': 'Dent_S2',
        'Peeling_S1': 'Peeling_S1',
        'Peeling_S2': 'Peeling_S2',
        'Vertical Scratch_S1': 'Vertical Scratch_S1',
        'Horizontal Scratch_S1': 'Horizontal Scratch_S1',
        'Vertical Scratch_S2': 'Vertical Scratch_S2',
        'Horizontal Scratch_S2': 'Horizontal Scratch_S2',
        'Corner Folding (Right)_S1': 'Corner Folding (Right)_S1',
        'Corner Folding (Left)_S1': 'Corner Folding (Left)_S1',
        'Corner Folding (Right)_S2': 'Corner Folding (Right)_S2',
        'Corner Folding (Left)_S2': 'Corner Folding (Left)_S2',
        'Horizontal Folding Line_S1': 'Horizontal Folding Line_S1',
        'Paper Crumpled': 'Paper Crumpled',
        'Paper Folding': 'Paper Folding',
        'TOF Skew': 'TOF Skew',
        'Crease line_S1': 'Crease line_S1',
        'Crease line_S2': 'Crease line_S2',
        'Roller Mark_S1': 'Roller Mark_S1',
        'Roller Mark_S2': 'Roller Mark_S2',
        'Pick Tire Mark': 'Pick Tire Mark',
        'Carriage Smear Minor_S1': 'Carriage Smear Minor_S1',
        'Carriage Smear Moderate_S1': 'Carriage Smear Moderate_S1',
        'Carriage Smear Severe_S1': 'Carriage Smear Severe_S1',
        'Carriage Smear Minor_S2': 'Carriage Smear Minor_S2',
        'Carriage Smear Moderate_S2': 'Carriage Smear Moderate_S2',
        'Carriage Smear Severe_S2': 'Carriage Smear Severe_S2',
        'Ink Smear Minor_S1': 'Ink Smear Minor_S1',
        'Ink Smear Moderate_S1': 'Ink Smear Moderate_S1',
        'Ink Smear Severe_S1': 'Ink Smear Severe_S1',
        'Ink Smear Minor_S2': 'Ink Smear Minor_S2',
        'Ink Smear Moderate_S2': 'Ink Smear Moderate_S2',
        'Ink Smear Severe_S2': 'Ink Smear Severe_S2',
        'Back of Page Rib Smear': 'Back of Page Rib Smear',
        'Rib Stain': 'Rib Stain',
        'Aerosol Overspray': 'Aerosol Overspray',
        'Ink Transfer_S1': 'Ink Transfer_S1',
        'Ink Transfer_S2': 'Ink Transfer_S2',
        'Ink Stain_Minor_S1': 'Ink Stain_Minor_S1',
        'Ink Stain_Moderate_S1': 'Ink Stain_Moderate_S1',
        'Ink Stain_Severe_S1': 'Ink Stain_Severe_S1',
        'Ink Stain_Minor_S2': 'Ink Stain_Minor_S2',
        'Ink Stain_Moderate_S2': 'Ink Stain_Moderate_S2',
        'Ink Stain_Severe_S2': 'Ink Stain_Severe_S2',
        'Ink Smudge_S1': 'Ink Smudge_S1',
        'Ink Smudge_S2': 'Ink Smudge_S2',
        'Starwheel Damage_S1': 'Starwheel Damage_S1',
        'Starwheel Damage_S2': 'Starwheel Damage_S2',
        'Envelope Dent': 'Envelope Dent',
        'Envelope Flap Carriage Smear': 'Envelope Flap Carriage Smear',
        'Edge Catch (Left)_S1': 'Edge Catch (Left)_S1',
        'Edge Catch (Left)_S2': 'Edge Catch (Left)_S2',
        'Edge Catch (Right)_S1': 'Edge Catch (Right)_S1',
        'Edge Catch (Right)_S2': 'Edge Catch (Right)_S2',
        'Head Strike_S1': 'Head Strike_S1',
        'Head Strike_S2': 'Head Strike_S2',
        'Nick': 'Nick',
        'BOF_Line Shift Up': 'BOF_Line Shift Up',
        'MSD_BOF Missing Line_S1': 'MSD_BOF Missing Line_S1',
        'MSD_BOF Missing Line_S2': 'MSD_BOF Missing Line_S2',
        'Margin Shift_Up_S1': 'Margin Shift_Up_S1',
        'Margin Shift_Down_S1': 'Margin Shift_Down_S1',
        'Margin Shift_Left_S1': 'Margin Shift_Left_S1',
        'Margin Shift_Right_S1': 'Margin Shift_Right_S1',
        'Margin Shift_Up_S2': 'Margin Shift_Up_S2',
        'Margin Shift_Down_S2': 'Margin Shift_Down_S2',
        'Margin Shift_Left_S2': 'Margin Shift_Left_S2',
        'Margin Shift_Right_S2': 'Margin Shift_Right_S2',
        'Obvious Skew_S1': 'Obvious Skew_S1',
        'Obvious Skew_S2': 'Obvious Skew_S2'
    },
    threshold_specs={
        'Plain': {
            'Simplex': 5,
            'Duplex': 10
        },
        'Brochure': {
            'Simplex': 5,
            'Duplex': 10
        },
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total Soft Error"
)

SKEW_CONFIG = TestCategoryConfig(
    name="Skew",
    error_column_config={
        'TOF_A>B_S1': ['TOF_A>B_S1', 'TOF_A>B_S2'],
        'TOF_B>A_S1': ['TOF_B>A_S1', 'TOF_B>A_S2'],
        'SOF_A>C_S1': ['SOF_A>C_S1', 'SOF_A>C_S2'],
        'SOF_C>A_S1': ['SOF_C>A_S1', 'SOF_C>A_S2'],
        'TOF+SOF_A>B + C>A_S1': ['TOF+SOF_A>B + C>A_S1', 'TOF+SOF_A>B + C>A_S2'],
        'TOF+SOF_B>A + A>C_S1': ['TOF+SOF_B>A + A>C_S1', 'TOF+SOF_B>A + A>C_S2'],
        'FEED SKEW_C>D_S1': ['FEED SKEW_C>D_S1', 'FEED SKEW_C>D_S2'],
        'FEED SKEW_D>C_S1': ['FEED SKEW_D>C_S1', 'FEED SKEW_D>C_S2']
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total Skew",
    additional_groupby_cols=['Print Quality']
)

OTHER_DEFECTS_CONFIG = TestCategoryConfig(
    name="Other Defects",
    error_column_config={
        'Blank Page Eject': 'Blank Page Eject',
        'Carriage Stall_S1': 'Carriage Stall_S1',
        'Carriage Stall_S2': 'Carriage Stall_S2',
        'Carriage Jam_S1': 'Carriage Jam_S1',
        'Carriage Jam_S2': 'Carriage Jam_S2',
        'PHA Issue': 'PHA Issue',
        'Ink Supply Failure': 'Ink Supply Failure',
        'Size Mismatch Error (Width)': 'Size Mismatch Error (Width)',
        'Size Mismatch Error (Length)': 'Size Mismatch Error (Length)',
        'Printer Hang': 'Printer Hang',
        'False Paper Jam': 'False Paper Jam',
        'False Out of Paper': 'False Out of Paper',
        'Abnormal Noise': 'Abnormal Noise',
        'Error Page (Corrupted Printout)': 'Error Page (Corrupted Printout)',
        'Incomplete Printing _S1': 'Incomplete Printing _S1',
        'Incomplete Printing _S2': 'Incomplete Printing _S2',
        'Blackout': 'Blackout',
        'BOF_Corrupted Printout': 'BOF_Corrupted Printout',
        'False Pen Failure': 'False Pen Failure',
        'Linefeed Shaft Shifted Causing No Pick': 'Linefeed Shaft Shifted Causing No Pick',
        'Media Mismatch': 'Media Mismatch',
        'Media Size Mismatch': 'Media Size Mismatch',
        'Pen Failure': 'Pen Failure',
        'Rear Door Pop Out': 'Rear Door Pop Out',
        'Unable To Duplex': 'Unable To Duplex',
        'Auto Shut Down': 'Auto Shut Down',
        'Hands Off': 'Hands Off',
        'Start/Stop Defect': 'Start/Stop Defect',
        'Service Station Stall': 'Service Station Stall',
        'Auto Job Cancel': 'Auto Job Cancel',
        'Auto Power Cycle': 'Auto Power Cycle',
        'Paper out of order': 'Paper out of order'
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total Other Defects"
)

PQ_CONFIG = TestCategoryConfig(
    name="PQ",
    error_column_config={
        'Horizontal Light Band_Minor_S1': 'Horizontal Light Band_Minor_S1',
        'Horizontal Light Band_Moderate_S1': 'Horizontal Light Band_Moderate_S1',
        'Horizontal Light Band_Severe_S1': 'Horizontal Light Band_Severe_S1',
        'Horizontal Light Band_Minor_S2': 'Horizontal Light Band_Minor_S2',
        'Horizontal Light Band_Moderate_S2': 'Horizontal Light Band_Moderate_S2',
        'Horizontal Light Band_Severe_S2': 'Horizontal Light Band_Severe_S2',
        'Horizontal Dark Band_Minor_S1': 'Horizontal Dark Band_Minor_S1',
        'Horizontal Dark Band_Moderate_S1': 'Horizontal Dark Band_Moderate_S1',
        'Horizontal Dark Band_Severe_S1': 'Horizontal Dark Band_Severe_S1',
        'Horizontal Dark Band_Minor_S2': 'Horizontal Dark Band_Minor_S2',
        'Horizontal Dark Band_Moderate_S2': 'Horizontal Dark Band_Moderate_S2',
        'Horizontal Dark Band_Severe_S2': 'Horizontal Dark Band_Severe_S2',
        'Horizontal Grainy_Minor_S1': 'Horizontal Grainy_Minor_S1',
        'Horizontal Grainy_Moderate_S1': 'Horizontal Grainy_Moderate_S1',
        'Horizontal Grainy_Severe_S1': 'Horizontal Grainy_Severe_S1',
        'Horizontal Grainy_Minor_S2': 'Horizontal Grainy_Minor_S2',
        'Horizontal Grainy_Moderate_S2': 'Horizontal Grainy_Moderate_S2',
        'Horizontal Grainy_Severe_S2': 'Horizontal Grainy_Severe_S2',
        'Vertical Banding_S1': 'Vertical Banding_S1',
        'Vertical Banding_S2': 'Vertical Banding_S2',
        'Micro Horizontal Banding_S1': 'Micro Horizontal Banding_S1',
        'Micro Horizontal Banding_S2': 'Micro Horizontal Banding_S2',
        'Gradient Banding_S1': 'Gradient Banding_S1',
        'Gradient Banding_S2': 'Gradient Banding_S2',
        'Black Bar': 'Black Bar',
        'Light SBB_S1': 'Light SBB_S1',
        'Light SBB_S2': 'Light SBB_S2',
        'Dark SBB_S1': 'Dark SBB_S1',
        'Dark SBB_S2': 'Dark SBB_S2',
        'Ink Starvation _S1': 'Ink Starvation _S1',
        'Ink Starvation _S2': 'Ink Starvation _S2',
        'Ink Drops': 'Ink Drops',
        'Ink Mixing_S1': 'Ink Mixing_S1',
        'Ink Mixing_S2': 'Ink Mixing_S2',
        'Massive Nozzle Out': 'Massive Nozzle Out',
        'Nozzle Out_Minor_S1': 'Nozzle Out_Minor_S1',
        'Nozzle Out_Moderate_S1': 'Nozzle Out_Moderate_S1',
        'Nozzle Out_Severe_S1': 'Nozzle Out_Severe_S1',
        'Nozzle Out_Minor_S2': 'Nozzle Out_Minor_S2',
        'Nozzle Out_Moderate_S2': 'Nozzle Out_Moderate_S2',
        'Nozzle Out_Severe_S2': 'Nozzle Out_Severe_S2',
        'Pen Alignment_S1': 'Pen Alignment_S1',
        'Pen Alignment_S2': 'Pen Alignment_S2',
        'Bidi Misalignment_S1': 'Bidi Misalignment_S1',
        'Bidi Misalignment_S2': 'Bidi Misalignment_S2',
        'Worms PQ': 'Worms PQ',
        'MOFTE_S1': 'MOFTE_S1',
        'MOFTE_S2': 'MOFTE_S2',
        'BOFTE_S1': 'BOFTE_S1',
        'BOFTE_S2': 'BOFTE_S2',
        'SEPTE': 'SEPTE',
        'Hue Shift_S1': 'Hue Shift_S1',
        'Hue Shift_S2': 'Hue Shift_S2',
        'Bleeding': 'Bleeding',
        'Mottling _S1': 'Mottling _S1',
        'Mottling _S2': 'Mottling _S2',
        'Fuzzy Text_Minor_S1': 'Fuzzy Text_Minor_S1',
        'Fuzzy Text_Moderate_S1': 'Fuzzy Text_Moderate_S1',
        'Fuzzy Text_Severe_S1': 'Fuzzy Text_Severe_S1',
        'Fuzzy Text_Minor_S2': 'Fuzzy Text_Minor_S2',
        'Fuzzy Text_Moderate_S2': 'Fuzzy Text_Moderate_S2',
        'Fuzzy Text_Severe_S2': 'Fuzzy Text_Severe_S2',
        'Blurry Printout': 'Blurry Printout',
        'Double Print': 'Double Print',
        'Pen Starvation': 'Pen Starvation',
        'Print Split': 'Print Split',
        'Text Offset': 'Text Offset',
        'TOFTE_S1': 'TOFTE_S1',
        'TOFTE_S2': 'TOFTE_S2',
        'Unexpected Print': 'Unexpected Print',
        'Double Vision_S1': 'Double Vision_S1',
        'Double Vision_S2': 'Double Vision_S2',
        'Color Missing': 'Color Missing',
        'Wrong color': 'Wrong color',
        'Half Die Color Missing': 'Half Die Color Missing',
        'ImageShift_FW': 'ImageShift_FW'
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total Output Spillage"
)

# ============================================================================
# ADF CATEGORY DEFINITIONS
# ============================================================================

ADF_INTERVENTION_CONFIG = TestCategoryConfig(
    name="ADF Intervention",
    error_column_config={
        'ADF No Pick': ['ADF No Pick_Top (Top 5 sheets)', 'ADF No Pick_Middle', 'ADF No Pick_Bottom (Last 5 sheets)', 'ADF No Pick_ Last Sheet'],
        'ADF Multipick': ['ADF MP_Top (Top 5 sheets)', 'ADF MP_Middle', 'ADF MP_Bottom (Last 5 sheets)', 'ADF MP_2nd Last sheets'],
        'ADF Jam': ['ADF Jam Z1', 'ADF Jam_Z2', 'ADF Jam_Z3', 'ADF Jam_Z4', 'ADF Jam_Z5', 'ADF Jam_Z6', 'ADF Jam_Z7'],
        'ADF Stall': ['ADF Stall_Z1', 'ADF Stall_Z2', 'ADF Stall_Z3', 'ADF Stall_Z4', 'ADF Stall_Z5', 'ADF Stall_Z6', 'ADF Stall_Z7']
    },
    threshold_specs={
        'Plain': 0.58,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 10
    },
    total_column_name="Sum of Total ADF Intervention"
)

ADF_SOFT_ERROR_CONFIG = TestCategoryConfig(
    name="ADF Soft Error",
    error_column_config={
        'Target Dent': 'Target Dent',
        'Target Tear': 'Target Tear',
        'Target Peeling': 'Target Peeling',
        'Target Scratch': 'Target Scratch',
        'Target Corner Folding (Left)': 'Target Corner Folding (Left)',
        'Target Corner Folding (Right)': 'Target Corner Folding (Right)',
        'Target Edge Catch': 'Target Edge Catch',
        'Target Roller Mark': 'Target Roller Mark',
        'Target Folding Line (Horizontal)': 'Target Folding Line (Horizontal)',
        'Target Folding Line (Vertical)': 'Target Folding Line (Vertical)',
        'Target Folding Edge (Left)': 'Target Folding Edge (Left)',
        'Target Folding Edge (Right)': 'Target Folding Edge (Right)',
        'Target Other Damage': 'Target Other Damage',
        'Target Pick tire marks': ['Target Pick Tire Marks_S1', 'Target Pick Tire Marks_S2', 'Target Crease'],
        'Target Bull Dozing': 'Target Bull Dozing',
        'Target Output Messy': 'Target Output Messy',
        'Target Fallen Sheet': 'Target Fallen Sheet',
        'Target Unable to Eject Fully': 'Target Unable to Eject Fully',
        'Target Incorrect Sequence': 'Target Incorrect Sequence',
        'Target Sucked Back': 'Target Sucked Back',
        'MB_Margin Shift up': ['MB_Margin Shift up_S1', 'MB_Margin Shift up_S2'],
        'MB_Margin Shift down': ['MB_Margin Shift down_S1', 'MB_Margin Shift down_S2'],
        'MB_Margin Shift left': ['MB_Margin Shift left_S1', 'MB_Margin Shift left_S2'],
        'MB_Margin Shift right': ['MB_Margin Shift right_S1', 'MB_Margin Shift right_S2'],
        'NMB_Margin Shift up': ['NMB_Margin Shift up_S1', 'NMB_Margin Shift up_S2'],
        'NMB_Margin Shift down': ['NMB_Margin Shift down_S1', 'NMB_Margin Shift down_S2'],
        'NMB_Margin Shift left': ['NMB_Margin Shift left_S1', 'NMB_Margin Shift left_S2'],
        'NMB_Margin Shift right': ['NMB_Margin Shift right_S1', 'NMB_Margin Shift right_S2'],
        'Obvious Image Skew': ['Obvious Image Skew_S1', 'Obvious Image Skew_S2'],
        'Wavy Line': ['Wavy Line_S1', 'Wavy Line_S2'],
        'ADF TOF Drag': ['ADF TOF Drag_S1', 'ADF TOF Drag_S2'],
        'ADF Bottom Drag': ['ADF Bottom Drag_S1', 'ADF Bottom Drag_S2'],
        'FB TOF Drag_S1': 'FB TOF Drag_S1',
        'FB Bottom Drag_S1': 'FB Bottom Drag_S1'
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total ADF Soft Error"
)

ADF_IMAGE_QUALITY_CONFIG = TestCategoryConfig(
    name="ADF Image Quality",
    error_column_config={
        '1 Vertical Line': ['1 Vertical Line_S1', '1 Vertical Line_(S1)', '1 Vertical Line_S2', '1 Vertical Line_(S2)'],
        'Multiple Vertical Lines': ['Multiple Vertical Lines_S1', 'Multiple Vertical Lines_(S1)', 'Multiple Vertical Lines_S2', 'Multiple Vertical Lines_(S2)'],
        '1 Vertical Streak': ['1 Vertical Streak_S1', '1 Vertical Streak_S2'],
        'Multiple Vertical Streaks': ['Multiple Vertical Streaks_S1', 'Multiple Vertical Streaks_S2'],
        '1 Vertical Broken Line': ['1 Vertical Broken Line_S1', '1 Vertical Broken Line_(S1)', '1 Vertical Broken Line_S2', '1 Vertical Broken Line_(S2)'],
        'Additional Vertical Line': ['Additional Vertical Line_S1', 'Additional Vertical Line_S2'],
        '1 Horizontal Line': ['1 Horizontal Line_S1', '1 Horizontal Line_S2'],
        'Multiple Horizontal Lines': ['Multiple Horizontal Lines_S1', 'Multiple Horizontal Lines_(S1)', 'Multiple Horizontal Lines_S2', 'Multiple Horizontal Lines_(S2)'],
        '1 Horizontal Streak': ['1 Horizontal Streak_S1', '1 Horizontal Streak_S2'],
        'Multiple Horizontal Streaks': ['Multiple Horizontal Streaks_S1', 'Multiple Horizontal Streaks_(S1)', 'Multiple Horizontal Streaks_S2', 'Multiple Horizontal Streaks_(S2)'],
        'Horizontal Broken Line': ['Horizontal Broken Line_S1', 'Horizontal Broken Line_S2'],
        'Multiple Horizontal Broken Lines': ['Multiple Horizontal Broken Lines_S1', 'Multiple Horizontal Broken Lines_S2'],
        'Additional Horizontal Line On BOF': 'Additional Horizontal Line On BOF',
        'Blank Page Scan Image': 'Blank Page Scan Image',
        'Corrupted Scan Image': 'Corrupted Scan Image',
        'Partial Scan Image': 'Partial Scan Image',
        '0KB images': '0KB images',
        'Missing Images': 'Missing Images',
        'Job Auto Cancel': 'Job Auto Cancel',
        'Shadow on Scan Image': ['Shadow on Scan Image_S1', 'Shadow on Scan Image_S2'],
        'Color Swopped': ['Color Swopped_S1', 'Color Swopped_S2'],
        'Background Image': ['Background Image_S1', 'Background Image_S2'],
        'Text Slanted': ['Text Slanted_S1', 'Text Slanted_S2'],
        'White Vertical Line_S1': 'White Vertical Line_S1',
        'White Vertical Line_S2': 'White Vertical Line_S2',
        'Image Distort BOF': ['Image Distort BOF', 'Image Crop BOF'],
        'Image Distort TOF': ['Image Distort TOF', 'Image Crop TOF']
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total ADF Image Quality"
)

ADF_OTHER_ISSUE_CONFIG = TestCategoryConfig(
    name="ADF Other Issue",
    error_column_config={
        'False Detection': 'False Detection',
        'False DFJ': 'False DFJ',
        'Scanner Failure': 'Scanner Failure',
        'Scanner Stall': 'Scanner Stall',
        'Fit to Page Failure': 'Fit to Page Failure',
        'Unable to Scan': 'Unable to Scan',
        'Start Stop Defect': 'Start Stop Defect',
        'Printer Hang': 'Printer Hang',
        'Auto Shut Down': 'Auto Shut Down',
        'Auto Restart': 'Auto Restart',
        'Auto Cancel': 'Auto Cancel',
        'Scanner_Abnormal Noise': 'Scanner_Abnormal Noise',
        'Target Duplex Failed': 'Target Duplex Failed',
        'Double Image': ['Double Image_S1', 'Double Image_S2'],
        'Image Distort': ['Image Distort_S1', 'Image Distort_S2'],
        'Wrong Text Size': 'Wrong Text Size',
        'Line Cut Off': ['Line Cut Off_S1', 'Line Cut Off_S2'],
        'Abnormal Image Color': 'Abnormal Image Color',
        'Dark Scan': 'Dark Scan',
        'ADF Late Pick': 'ADF Late Pick',
        'ADF Sensor not Working': 'ADF Sensor not Working',
        'ADF Unresponsive': 'ADF Unresponsive',
        'Horizontal Target Edge Image': 'Horizontal Target Edge Image',
        'Dust Under Glass and Cannot Clean': 'Dust Under Glass and Cannot Clean',
        'Image Not Transfer': 'Image Not Transfer',
        'Page Split': 'Page Split',
        'Data Corrupted': 'Data Corrupted',
        'extra blank page': 'extra blank page',
        'Scanner Unresponsive': 'Scanner Unresponsive',
        'False TOF Detection': 'False TOF Detection',
        'ADF Hand Off_Z1': 'ADF Hand Off_Z1',
        'ADF Hand Off_Z2': 'ADF Hand Off_Z2',
        'ADF Hand Off_Z3': 'ADF Hand Off_Z3',
        'ADF Hand Off_Z4': 'ADF Hand Off_Z4',
        'ADF Hand Off_Z5': 'ADF Hand Off_Z5',
        'ADF Hand Off_S1': 'ADF Hand Off_S1',
        'ADF Hand Off_S2': 'ADF Hand Off_S2',
        'Black Bar_S1': 'Black Bar_S1',
        'Black Bar_S2': 'Black Bar_S2',
        'Top Black Bar_S1': 'Top Black Bar_S1',
        'Top Black Bar_S2': 'Top Black Bar_S2'
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total ADF Other Issue"
)

ADF_SKEW_CONFIG = TestCategoryConfig(
    name="ADF Skew",
    error_column_config={
        'Obvious COPY TOP skew (>20)_Copy _S1': 'Obvious COPY TOP skew (>20)_Copy _S1',
        'Obvious COPY TOP skew (<20)_Copy _S1': 'Obvious COPY TOP skew (<20)_Copy _S1',
        'Obvious COPY TOP skew (<-20)_Copy _S1': 'Obvious COPY TOP skew (<-20)_Copy _S1',
        'Obvious COPY TOP skew (<10)_Copy _S1': 'Obvious COPY TOP skew (<10)_Copy _S1',
        'Obvious COPY TOP skew (<-10)_Copy _S1': 'Obvious COPY TOP skew (<-10)_Copy _S1',
        'Obvious COPY SIDE skew (>20)_Copy _S1': 'Obvious COPY SIDE skew (>20)_Copy _S1',
        'Obvious COPY SIDE skew (<20)_Copy _S1': 'Obvious COPY SIDE skew (<20)_Copy _S1',
        'Obvious COPY SIDE skew (<-20)_Copy _S1': 'Obvious COPY SIDE skew (<-20)_Copy _S1',
        'Obvious COPY SIDE skew (<10)_Copy _S1': 'Obvious COPY SIDE skew (<10)_Copy _S1',
        'Obvious COPY SIDE skew (<-10)_Copy _S1': 'Obvious COPY SIDE skew (<-10)_Copy _S1',
        'Obvious COPY FEED skew (>10)_Copy _S1': 'Obvious COPY FEED skew (>10)_Copy _S1',
        'Obvious COPY FEED skew (<10)_Copy _S1': 'Obvious COPY FEED skew (<10)_Copy _S1',
        'Obvious COPY FEED skew (<-10)_Copy _S1': 'Obvious COPY FEED skew (<-10)_Copy _S1'
    },
    threshold_specs={
        'Plain': 5,
        'Brochure': 5,
        'Photo': 5,
        'Card': 5,
        'Envelope': 5
    },
    total_column_name="Sum of Total ADF Skew"
)

# ============================================================================
# CATEGORY LISTS
# ============================================================================

# CUSLT test categories
CUSLT_TEST_CATEGORIES = [
    INTERVENTION_CONFIG,
    SOFT_ERROR_CONFIG,
    SKEW_CONFIG,
    OTHER_DEFECTS_CONFIG,
    PQ_CONFIG
]

# ADF test categories
ADF_TEST_CATEGORIES = [
    ADF_INTERVENTION_CONFIG,
    ADF_SOFT_ERROR_CONFIG,
    ADF_IMAGE_QUALITY_CONFIG,
    ADF_OTHER_ISSUE_CONFIG,
    ADF_SKEW_CONFIG
]