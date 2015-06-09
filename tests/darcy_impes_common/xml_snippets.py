
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
