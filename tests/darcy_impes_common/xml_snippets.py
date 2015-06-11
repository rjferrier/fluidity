
wall_no_normal_flow_bc = """
        <boundary_conditions name="wall_flow">
          <surface_ids>
            <integer_value shape="$WALL_NUM" rank="1">$WALL_IDS</integer_value>
          </surface_ids>
          <type name="no_normal_flow"/>
        </boundary_conditions>"""

sat_face_value_fe_sweby = """
        <face_value name="FiniteElement">
          <limit_face_value>
            <limiter name="Sweby"/>
          </limit_face_value>
        </face_value>"""

gravity = """
    <gravity>
      <magnitude>
        <real_value rank="0">1.5e+06</real_value>
      </magnitude>
      <vector_field name="GravityDirection" rank="1">
        <prescribed>
          <mesh name="ElementWiseMesh"/>
          <value name="WholeMesh">
            <constant>
              <real_value shape="$DIM_NUMBER" dim1="dim" rank="1">$GRAVITY_DIRECTION</real_value>
            </constant>
          </value>
        </prescribed>
      </vector_field>
    </gravity>"""

corey_relperm_correlation = """
        <correlation name="Corey2Phase"/>"""

quadratic_relperm_correlation = """
        <correlation name="PowerLaw">
          <exponents>
            <real_value shape="2" rank="1">2.0 2.0</real_value>
          </exponents> $RESIDUAL_SATURATIONS
        </correlation>"""

residual_saturations = """
          <residual_saturations>
            <real_value shape="2" rank="1">$RESIDUAL_SATURATION1 $RESIDUAL_SATURATION2</real_value>
          </residual_saturations>"""

error_variable = """
    <scalar_field name="LinearInterpolatedAnalytical{2}Solution">
      <prescribed>
        <mesh name="PressureMesh"/>
        <value name="WholeMesh">
          <python>
            <string_value lines="20" type="code" language="python">def val(X, t):
   from sys import path
   path.append('../darcy_impes_common/')
   from buckley_leverett_test_tools import interp_using_analytic
   afname = "reference_solution/{0}_{1}.txt"
   return interp_using_analytic(X[0], afname)</string_value>
          </python>
        </value>
        <stat>
          <include_cv_stats/>
        </stat>
        <do_not_recalculate/>
      </prescribed>
    </scalar_field>
    <scalar_field name="{2}AbsError">
      <diagnostic>
        <mesh name="PressureMesh"/>
        <algorithm source_field_2_type="scalar" name="scalar_difference" source_field_1_name="{2}" source_field_2_name="LinearInterpolatedAnalytical{2}Solution" material_phase_support="single" source_field_1_type="scalar">
          <absolute_difference/>
        </algorithm>
        <stat>
          <include_cv_stats/>
        </stat>
        <consistent_interpolation/>
      </diagnostic>
    </scalar_field>"""
