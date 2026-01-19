"""
Each test category defines its error columns and how to process them.
"""

class TestCategoryConfig:
    """
    Configuration for a single test category.
    """
    
    def __init__(self, name, error_column_config, threshold_specs, total_column_name, additional_groupby_cols=None):
        """
        Args:
            name: Display name for the test category
            error_column_config: Dict mapping output column names to input column specs
                - For single column: {'Output Name': 'Raw Column Name'}
                - For summed columns: {'Output Name': ['Col1', 'Col2', 'Col3']}
            threshold_specs: Dict mapping media types to their thresholds
            total_column_name: Name for the total column
        """
        self.name = name
        self.error_column_config = error_column_config
        self.threshold_specs = threshold_specs
        self.total_column_name = total_column_name
        self.additional_groupby_cols = additional_groupby_cols or []

        self._uses_print_mode = self._check_print_mode_usage()
    
    def _check_print_mode_usage(self):
        """Check if any threshold uses print mode (is a dict)."""
        for value in self.threshold_specs.values():
            if isinstance(value, dict):
                return True
        return False

    def get_spec_for_media_type(self, media_type, print_mode=None):
        """
        Get threshold spec for media type and optionally print mode.
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
# TEST CATEGORY DEFINITIONS
# ============================================================================

INTERVENTION_CONFIG = TestCategoryConfig(
    name="Intervention",
    error_column_config={
        'NP': ['NP_Top', 'NP_Middle', 'NP_Bottom1', 'NP_Bottom2', 'NP_Last Page'],
        'MP': ['MP_Top', 'MP_Middle', 'MP_Bottom1', 'MP_Bottom2', 'MP_Last page', 'MMP_Top', 'MMP_Middle', 'MMP_Bottom1', 'MMP_Bottom2', 'MMP_Last page'],
        'TP': ['TP_Top', 'TP_Middle', 'TP_Bottom1', 'TP_Bottom2', 'TP_Last Page'],
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

# List of all test categories to process
ALL_TEST_CATEGORIES = [
    INTERVENTION_CONFIG,
    SOFT_ERROR_CONFIG,
    SKEW_CONFIG,
    OTHER_DEFECTS_CONFIG,
    PQ_CONFIG
    # Add more configs here as you define them
]