using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using DesktopApp.ViewModels;
using DesktopApp.Views;

namespace DesktopApp;

public class App : Application
{
    private MainWindowViewModel? _vm;

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            _vm = new MainWindowViewModel();

            // Set DataContext for tray icon commands
            DataContext = _vm;

            var args = desktop.Args ?? [];
            var startMinimized = _vm.Settings.StartMinimized
                || args.Contains("--minimized");

            desktop.MainWindow = new MainWindow
            {
                DataContext = _vm,
                ShowInTaskbar = !startMinimized,
                WindowState = startMinimized ? WindowState.Minimized : WindowState.Normal,
            };

            if (!startMinimized)
                desktop.MainWindow.Show();

            // Handle window close: hide to tray instead of quitting when MinimizeToTray is on
            desktop.MainWindow.Closing += (_, e) =>
            {
                if (_vm.Settings.MinimizeToTray)
                {
                    e.Cancel = true;
                    desktop.MainWindow.Hide();
                }
            };

            desktop.Exit += async (_, _) =>
            {
                await _vm.DisposeAsync();
            };
        }

        base.OnFrameworkInitializationCompleted();
    }
}
