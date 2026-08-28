import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layout/AppLayout";
import { RequireAuth, RequirePermission } from "./auth/guards";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TestsPage } from "./pages/TestsPage";
import { TestDetailPage } from "./pages/TestDetailPage";
import { PlatformsPage } from "./pages/PlatformsPage";
import { TagsPage } from "./pages/TagsPage";
import { UsersPage } from "./pages/UsersPage";
import { ProfilePage } from "./pages/ProfilePage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/tests" replace />} />
          <Route path="/tests" element={<TestsPage />} />
          <Route path="/tests/:testId" element={<TestDetailPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          <Route element={<RequirePermission anyOf={["platform:read"]} />}>
            <Route path="/platforms" element={<PlatformsPage />} />
          </Route>
          <Route element={<RequirePermission anyOf={["tag:manage"]} />}>
            <Route path="/tags" element={<TagsPage />} />
          </Route>
          <Route element={<RequirePermission anyOf={["user:read_any", "user:update_any"]} />}>
            <Route path="/users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/tests" replace />} />
    </Routes>
  );
}
