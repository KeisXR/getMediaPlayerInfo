using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DesktopApp.Models;

namespace DesktopApp.ViewModels;

/// <summary>
/// ViewModel for the History tab.
/// Maintains a chronological log of played tracks and provides export actions.
/// </summary>
public partial class HistoryViewModel : ViewModelBase
{
    private const int MaxHistoryEntries = 500;

    [ObservableProperty] private string _searchText = string.Empty;
    [ObservableProperty] private ObservableCollection<HistoryEntry> _entries = [];
    [ObservableProperty] private ObservableCollection<HistoryEntry> _filteredEntries = [];

    private readonly object _lock = new();

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /// <summary>Add a new entry. Thread-safe.</summary>
    public void AddEntry(HistoryEntry entry)
    {
        lock (_lock)
        {
            Entries.Insert(0, entry);

            // Enforce capacity
            while (Entries.Count > MaxHistoryEntries)
                Entries.RemoveAt(Entries.Count - 1);
        }

        ApplyFilter();
    }

    partial void OnSearchTextChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        var q = SearchText.Trim().ToLowerInvariant();

        lock (_lock)
        {
            var filtered = string.IsNullOrWhiteSpace(q)
                ? Entries.ToList()
                : Entries.Where(e =>
                    e.Title.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                    e.Artist.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                    e.Album.Contains(q, StringComparison.OrdinalIgnoreCase) ||
                    e.SourceApp.Contains(q, StringComparison.OrdinalIgnoreCase)).ToList();

            FilteredEntries = new ObservableCollection<HistoryEntry>(filtered);
        }
    }

    // -----------------------------------------------------------------------
    // Commands
    // -----------------------------------------------------------------------

    [RelayCommand]
    private void Clear()
    {
        lock (_lock)
            Entries.Clear();
        FilteredEntries.Clear();
    }

    [RelayCommand]
    private async Task ExportCsv()
    {
        var path = await PickSaveFileAsync("history.csv", "CSV Files", "*.csv");
        if (path is null)
            return;

        var sb = new StringBuilder();
        sb.AppendLine("Timestamp,Title,Artist,Album,Source,Duration,Connection");

        lock (_lock)
        {
            foreach (var e in Entries)
            {
                sb.AppendLine(string.Join(",",
                    CsvEscape(e.TimestampDisplay),
                    CsvEscape(e.Title),
                    CsvEscape(e.Artist),
                    CsvEscape(e.Album),
                    CsvEscape(e.SourceApp),
                    CsvEscape(e.DurationDisplay),
                    CsvEscape(e.ConnectionName)));
            }
        }

        await File.WriteAllTextAsync(path, sb.ToString(), Encoding.UTF8);
    }

    [RelayCommand]
    private async Task ExportJson()
    {
        var path = await PickSaveFileAsync("history.json", "JSON Files", "*.json");
        if (path is null)
            return;

        List<HistoryEntry> snapshot;
        lock (_lock)
            snapshot = Entries.ToList();

        var options = new JsonSerializerOptions { WriteIndented = true };
        var json = JsonSerializer.Serialize(snapshot, options);
        await File.WriteAllTextAsync(path, json, Encoding.UTF8);
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private static string CsvEscape(string value)
    {
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n'))
            return $"\"{value.Replace("\"", "\"\"")}\"";
        return value;
    }

    private static async Task<string?> PickSaveFileAsync(
        string suggestedName, string filterName, string filterPattern)
    {
        if (Application.Current?.ApplicationLifetime is not IClassicDesktopStyleApplicationLifetime { MainWindow: { } win })
            return null;

        var topLevel = TopLevel.GetTopLevel(win);
        if (topLevel?.StorageProvider is not { } sp)
            return null;

        var file = await sp.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = "Export History",
            SuggestedFileName = suggestedName,
            FileTypeChoices =
            [
                new FilePickerFileType(filterName) { Patterns = [filterPattern] },
            ],
        });

        return file?.Path.LocalPath;
    }
}
