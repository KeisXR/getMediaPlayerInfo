using System.Collections.Generic;
using DesktopApp.Models;
using DesktopApp.ViewModels;
using Xunit;

namespace DesktopApp.Tests.ViewModels;

public class HistoryViewModelTests
{
    [Fact]
    public void AddEntry_AppearsAtFrontOfFilteredEntries()
    {
        var vm = new HistoryViewModel();
        var entry = new HistoryEntry { Title = "Test Song", Artist = "Artist" };

        vm.AddEntry(entry);

        Assert.Single(vm.FilteredEntries);
        Assert.Equal("Test Song", vm.FilteredEntries[0].Title);
    }

    [Fact]
    public void AddEntry_MultipleEntries_MostRecentFirst()
    {
        var vm = new HistoryViewModel();
        vm.AddEntry(new HistoryEntry { Title = "First" });
        vm.AddEntry(new HistoryEntry { Title = "Second" });
        vm.AddEntry(new HistoryEntry { Title = "Third" });

        Assert.Equal("Third",  vm.FilteredEntries[0].Title);
        Assert.Equal("Second", vm.FilteredEntries[1].Title);
        Assert.Equal("First",  vm.FilteredEntries[2].Title);
    }

    [Fact]
    public void SearchText_FiltersEntries()
    {
        var vm = new HistoryViewModel();
        vm.AddEntry(new HistoryEntry { Title = "Apple Song" });
        vm.AddEntry(new HistoryEntry { Title = "Banana Track" });
        vm.AddEntry(new HistoryEntry { Title = "Cherry Beat" });

        vm.SearchText = "banana";

        Assert.Single(vm.FilteredEntries);
        Assert.Equal("Banana Track", vm.FilteredEntries[0].Title);
    }

    [Fact]
    public void SearchText_EmptyString_ShowsAllEntries()
    {
        var vm = new HistoryViewModel();
        vm.AddEntry(new HistoryEntry { Title = "A" });
        vm.AddEntry(new HistoryEntry { Title = "B" });
        vm.SearchText = "A";
        vm.SearchText = "";

        Assert.Equal(2, vm.FilteredEntries.Count);
    }

    [Fact]
    public void Clear_RemovesAllEntries()
    {
        var vm = new HistoryViewModel();
        vm.AddEntry(new HistoryEntry { Title = "Song 1" });
        vm.AddEntry(new HistoryEntry { Title = "Song 2" });

        vm.ClearCommand.Execute(null);

        Assert.Empty(vm.Entries);
        Assert.Empty(vm.FilteredEntries);
    }
}
