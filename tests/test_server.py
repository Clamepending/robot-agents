from robot_policy_mcp.server import create_mcp_server


def test_create_mcp_server_name():
    server = create_mcp_server()
    assert server.name == "robot-policy"
