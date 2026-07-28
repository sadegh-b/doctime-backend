from app.main import app
from fastapi.routing import APIRoute

def dump_routes():
    print("=== Top-level routes ===")
    for i, route in enumerate(app.routes):
        route_type = type(route).__name__
        if isinstance(route, APIRoute):
            print(f"[{i}] APIRoute {route.methods} {route.path} name={route.name}")
        elif route_type == "_IncludedRouter":
            print(f"[{i}] _IncludedRouter")
            original = getattr(route, "original_router", None)
            print(f"    original_router type: {type(original).__name__}")
            if original is not None:
                inner_routes = getattr(original, "routes", None)
                print(f"    inner routes count: {len(inner_routes) if inner_routes is not None else 'None'}")
                if inner_routes:
                    for j, r in enumerate(inner_routes):
                        methods = getattr(r, "methods", [])
                        path = getattr(r, "path", "No Path")
                        name = getattr(r, "name", "No Name")
                        print(f"      [{j}] {methods} {path} name={name} type={type(r).__name__}")
        else:
            path = getattr(route, "path", "No Path")
            methods = getattr(route, "methods", [])
            print(f"[{i}] {route_type} {methods} {path}")

if __name__ == "__main__":
    dump_routes()
