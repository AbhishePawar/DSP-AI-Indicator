/**
 * DSP Design System (EPIC-F001) — shadcn-style primitives mapped to PR1.2 tokens.
 * Pure reusable UI. No business logic. No API calls.
 */

import { Button, buttonVariants } from "./forms/button";
import type { ButtonProps } from "./forms/button";
import { IconButton } from "./forms/icon-button";
import type { IconButtonProps } from "./forms/icon-button";
import { Input } from "./forms/input";
import type { InputProps } from "./forms/input";
import { PasswordInput } from "./forms/password-input";
import type { PasswordInputProps } from "./forms/password-input";
import { Textarea } from "./forms/textarea";
import type { TextareaProps } from "./forms/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./forms/select";
import { MultiSelect } from "./forms/multi-select";
import type { MultiSelectProps } from "./forms/multi-select";
import { Checkbox } from "./forms/checkbox";
import type { CheckboxProps } from "./forms/checkbox";
import { RadioGroup, RadioGroupItem } from "./forms/radio";
import { Switch } from "./forms/switch";
import type { SwitchProps } from "./forms/switch";
import { Slider } from "./forms/slider";
import type { SliderProps } from "./forms/slider";
import { DatePicker } from "./forms/date-picker";
import type { DatePickerProps } from "./forms/date-picker";
import { SearchBox } from "./forms/search-box";
import type { SearchBoxProps } from "./forms/search-box";
import { FormField } from "./forms/form-field";
import type { FormFieldProps } from "./forms/form-field";
import { ValidationMessage } from "./forms/validation-message";
import type { ValidationMessageProps } from "./forms/validation-message";

import { Badge } from "./data/badge";
import type { BadgeProps } from "./data/badge";
import { Avatar, AvatarFallback, AvatarImage } from "./data/avatar";
import { Tag } from "./data/tag";
import type { TagProps } from "./data/tag";
import { Chip } from "./data/chip";
import type { ChipProps } from "./data/chip";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./data/tooltip";
import { Popover, PopoverContent, PopoverTrigger } from "./data/popover";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "./data/dropdown-menu";
import { Pagination } from "./data/pagination";
import type { PaginationProps } from "./data/pagination";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./data/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "./data/accordion";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./data/table";
import { DataGrid } from "./data/data-grid";
import type { DataGridProps } from "./data/data-grid";
import { TreeView } from "./data/tree-view";
import type { TreeNode, TreeViewProps } from "./data/tree-view";

import { Container } from "./layout/container";
import type { ContainerProps } from "./layout/container";
import { Stack } from "./layout/stack";
import type { StackProps } from "./layout/stack";
import { Grid } from "./layout/grid";
import type { GridProps } from "./layout/grid";
import { Flex } from "./layout/flex";
import type { FlexProps } from "./layout/flex";
import { Section } from "./layout/section";
import type { SectionProps } from "./layout/section";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./layout/card-layout";
import { PageLayout } from "./layout/page-layout";
import type { PageLayoutProps } from "./layout/page-layout";

import { Typography } from "./typography/typography";
import type { TypographyProps } from "./typography/typography";

import { Sidebar, SidebarGroup, SidebarItem } from "./navigation/sidebar";
import type { SidebarItemProps, SidebarProps } from "./navigation/sidebar";
import { Header } from "./navigation/header";
import type { HeaderProps } from "./navigation/header";
import { Breadcrumb, BreadcrumbItem, BreadcrumbSeparator } from "./navigation/breadcrumb";
import { CommandPalette } from "./navigation/command-palette";
import type { CommandPaletteItem, CommandPaletteProps } from "./navigation/command-palette";
import { UserMenu } from "./navigation/user-menu";
import type { UserMenuProps } from "./navigation/user-menu";

import { Alert } from "./feedback/alert";
import type { AlertProps } from "./feedback/alert";
import { ToastProvider, ToastViewport, useToast } from "./feedback/toast";
import { Progress } from "./feedback/progress";
import type { ProgressProps } from "./feedback/progress";
import { Skeleton } from "./feedback/skeleton";
import type { SkeletonProps } from "./feedback/skeleton";
import { Spinner } from "./feedback/spinner";
import type { SpinnerProps } from "./feedback/spinner";
import { EmptyState } from "./feedback/empty-state";
import type { EmptyStateProps } from "./feedback/empty-state";
import { ErrorState } from "./feedback/error-state";
import type { ErrorStateProps } from "./feedback/error-state";
import { SuccessState } from "./feedback/success-state";
import type { SuccessStateProps } from "./feedback/success-state";
import { LoadingOverlay } from "./feedback/loading-overlay";
import type { LoadingOverlayProps } from "./feedback/loading-overlay";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "./dialogs/modal";
import { Drawer, DrawerContent, DrawerTrigger } from "./dialogs/drawer";
import type { DrawerProps } from "./dialogs/drawer";
import { ConfirmationDialog } from "./dialogs/confirmation-dialog";
import type { ConfirmationDialogProps } from "./dialogs/confirmation-dialog";
import { CommandDialog } from "./dialogs/command-dialog";
import type { CommandDialogProps } from "./dialogs/command-dialog";

import { ThemeSwitcher } from "./theme/theme-switcher";
import { DspThemeProvider, useNextTheme } from "./theme/dsp-theme-provider";
import { COMPONENT_CATALOGUE, DESIGN_SYSTEM_VERSION } from "./catalogue";

import { ChartContainer } from "./charts/chart-container";
import { ChartThemeWrapper } from "./charts/chart-theme-wrapper";
import { ResponsiveWrapper } from "./charts/responsive-wrapper";

import { DsIcons } from "./utilities/icons";
import { PermissionWrapper } from "./utilities/permission-wrapper";
import { HideBelow, ShowAbove, useMediaQuery } from "./utilities/responsive";
import { useKeyboardShortcut } from "./utilities/keyboard";
import { DsErrorBoundary } from "./utilities/error-boundary";
import { LoadingBlock } from "./utilities/loading";

export {
  Button, buttonVariants,
  IconButton,
  Input,
  PasswordInput,
  Textarea,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  MultiSelect,
  Checkbox,
  RadioGroup, RadioGroupItem,
  Switch,
  Slider,
  DatePicker,
  SearchBox,
  FormField,
  ValidationMessage,
  Badge,
  Avatar, AvatarFallback, AvatarImage,
  Tag,
  Chip,
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
  Popover, PopoverContent, PopoverTrigger,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
  Pagination,
  Tabs, TabsContent, TabsList, TabsTrigger,
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  DataGrid,
  TreeView,
  Container,
  Stack,
  Grid,
  Flex,
  Section,
  Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
  PageLayout,
  Typography,
  Sidebar, SidebarGroup, SidebarItem,
  Header,
  Breadcrumb, BreadcrumbItem, BreadcrumbSeparator,
  CommandPalette,
  UserMenu,
  Alert,
  ToastProvider, ToastViewport, useToast,
  Progress,
  Skeleton,
  Spinner,
  EmptyState,
  ErrorState,
  SuccessState,
  LoadingOverlay,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
  Drawer, DrawerContent, DrawerTrigger,
  ConfirmationDialog,
  CommandDialog,
  ThemeSwitcher,
  DspThemeProvider, useNextTheme,
  COMPONENT_CATALOGUE, DESIGN_SYSTEM_VERSION,
  ChartContainer,
  ChartThemeWrapper,
  ResponsiveWrapper,
  DsIcons,
  PermissionWrapper,
  HideBelow, ShowAbove, useMediaQuery,
  useKeyboardShortcut,
  DsErrorBoundary,
  LoadingBlock,
};

export type {
  ButtonProps,
  IconButtonProps,
  InputProps,
  PasswordInputProps,
  TextareaProps,
  MultiSelectProps,
  CheckboxProps,
  SwitchProps,
  SliderProps,
  DatePickerProps,
  SearchBoxProps,
  FormFieldProps,
  ValidationMessageProps,
  BadgeProps,
  TagProps,
  ChipProps,
  PaginationProps,
  DataGridProps,
  TreeNode, TreeViewProps,
  ContainerProps,
  StackProps,
  GridProps,
  FlexProps,
  SectionProps,
  PageLayoutProps,
  TypographyProps,
  SidebarItemProps, SidebarProps,
  HeaderProps,
  CommandPaletteItem, CommandPaletteProps,
  UserMenuProps,
  AlertProps,
  ProgressProps,
  SkeletonProps,
  SpinnerProps,
  EmptyStateProps,
  ErrorStateProps,
  SuccessStateProps,
  LoadingOverlayProps,
  DrawerProps,
  ConfirmationDialogProps,
  CommandDialogProps,
};
